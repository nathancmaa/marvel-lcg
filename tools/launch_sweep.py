"""Launch every scenario on a running dev server and check each reaches the
mulligan, with a different starter hero each time so every hero launches too.

The engine renders in lockstep with its table client: setup waits for a
websocket client and for an acknowledgement of every render. This script is
that client. It connects, says hello, and acknowledges each frame the moment
it arrives, so a launch takes about half a second rather than the animation
time a browser would spend.

Setup asks that some scenarios put (The Widow's Web, Hope's Captor, ...) are
answered with their first option. A setup error shows as a prompt starting
"Error occurred". An error while card abilities are built is fatal to the
server process: it exits with code 0 and the traceback is in its log, and
every later launch in the sweep then fails to connect.

    python tools/launch_sweep.py                        every scenario file
    python tools/launch_sweep.py rhino the_hood         names containing these
    python tools/launch_sweep.py --hero spider_man rhino
    python tools/launch_sweep.py --base http://127.0.0.1:2345

Needs the server already running (./run.sh, or the preview launcher).
Exit code is 0 when every launch reached the mulligan.
"""
import asyncio
import gzip
import json
import sys
import time
import urllib.parse
from pathlib import Path

import aiohttp

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from build import Build  # noqa: E402

BASE = "http://127.0.0.1:2345"
# Every route is gated on this cookie: the server's ui version,
# MAJOR.MINOR.PATCH.BUILD plus "r".
COOKIES = {"app_version": f"{Build.MAJOR}.{Build.MINOR}.{Build.PATCH}.{Build.BUILD}r"}
HEROES = sorted(p.stem for p in (ROOT / "deck" / "starter").glob("*.json"))


def hero_json(name: str) -> str:
    return (ROOT / "deck" / "starter" / f"{name}.json").read_text(encoding="utf-8")


def payload_for(path: Path, hero: str):
    """The payload the Quick Game page sends, underling merged in as solo.ts does."""
    scenario = json.loads(path.read_text(encoding="utf-8"))
    note = ""
    if scenario.get("underling_sets"):
        name = scenario["underling_sets"][0]
        under = json.loads((ROOT / "data" / "encounter_sets" / f"{name}.json").read_text(encoding="utf-8"))
        scenario["villain"] = under["expert_villain"] if scenario.get("expert") else under["villain"]
        scenario["set_aside"] = list(scenario.get("set_aside", [])) + list(under.get("set_aside", []))
        scenario["encounters"] = list(scenario.get("encounters", [])) + list(under.get("encounters", []))
        note = f"underling={name}"
    sets = list(dict.fromkeys(list(scenario.get("encounter_sets", [])) + list(scenario.get("modular_sets", []))))
    return {
        "campaign_json": json.dumps(scenario),
        "encounter_set_names": sets,
        "hero_json": [hero_json(hero)],
        "seed": -1,
        "timeout": 0,
        "challenges": [],
        "rules": ["v18_all"],
        "campaign_log": {},
    }, note


class Client:
    def __init__(self):
        self.session = None
        self.ws = None
        self.frames = 0
        self.game_id = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(cookies=COOKIES)
        self.ws = await self.session.ws_connect(BASE + "/ws?p=0")
        await self.ws.send_str("Connected")
        asyncio.create_task(self.drain())
        return self

    async def __aexit__(self, *exc):
        await self.ws.close()
        await self.session.close()

    async def drain(self):
        # Every frame the engine pushes is acknowledged at once, as the table
        # page does once it has drawn it. The ids come from the frame.
        try:
            async for msg in self.ws:
                if msg.type != aiohttp.WSMsgType.TEXT:
                    continue
                try:
                    frame = json.loads(msg.data)
                except Exception:
                    continue
                render_id = frame.get("render_id")
                game_id = frame.get("game_id")
                if render_id is None or game_id is None:
                    continue
                self.frames += 1
                self.game_id = game_id
                await self.get(f"/client_updated?p=0&r={render_id}&g={game_id}")
        except Exception as exc:
            print("websocket ended:", repr(exc)[:200], flush=True)

    async def get_json(self, path):
        async with self.session.get(BASE + path) as r:
            raw = await r.read()
            if r.headers.get("Content-Encoding") == "gzip" and raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            return r.status, (json.loads(raw) if raw else {})

    async def get(self, path):
        async with self.session.get(BASE + path) as r:
            return r.status, await r.text()

    async def post(self, body):
        async with self.session.post(BASE + "/post?p=0", data=body,
                                     headers={"Content-Type": "application/x-www-form-urlencoded"}) as r:
            return r.status

    async def run_one(self, path: Path, hero: str, budget: float = 90.0):
        payload, note = payload_for(path, hero)
        previous = self.game_id
        status, text = await self.get("/new?data=" + urllib.parse.quote(json.dumps(payload)))
        if status != 200:
            return "NEW-FAILED", f"{status} {text[:200]}"
        await self.ws.send_str("Connected")
        answered = []
        prompt = ""
        deadline = time.time() + budget
        # Until the engine has pushed a frame from the new game, the ask and
        # the world on offer are the last game's.
        while time.time() < deadline and self.game_id in (None, previous):
            await asyncio.sleep(0.05)
        if self.game_id in (None, previous):
            return "TIMEOUT", "no frame from the new game"
        while time.time() < deadline:
            try:
                _, world = await self.get_json("/get_world?p=0")
            except Exception:
                await asyncio.sleep(0.2)
                continue
            prompt = str(world.get("prompt") or "")
            if prompt.startswith("Error occurred"):
                return "ERROR", prompt.replace("\n", " | ")[:900]
            try:
                _, ask = await self.get_json("/get_ask?p=0")
            except Exception:
                ask = {}
            ask_prompt = str(ask.get("prompt_text") or "")
            if ask_prompt.startswith("Error occurred"):
                return "ERROR", ask_prompt.replace("\n", " | ")[:900]
            opts = ask.get("options_json")
            if opts:
                try:
                    options = json.loads(opts)
                except Exception:
                    options = []
                names = [o.get("name") for o in options]
                if "Resolve Mulligans" in names:
                    _, world = await self.get_json("/get_world?p=0")
                    hero_names = [c.get("name") for pl in world.get("players", []) for c in pl.get("area_hero", [])]
                    villains = [v.get("name") for v in world.get("area_villain", [])]
                    mains = [m.get("name") for m in world.get("area_schemes_main", [])]
                    detail = f"{'/'.join(hero_names)} vs {'/'.join(villains) or '(no villain)'}; main {'/'.join(mains)}"
                    if note:
                        detail += f"; {note}"
                    if answered:
                        detail += "; setup asks: " + "; ".join(answered)
                    # An identity and a main scheme on the table. Ids are not
                    # compared with the deck's: SP//dr's deck names 31001a/b
                    # and the table shows Peni Parker, 31002a.
                    if not hero_names or not mains:
                        wanted = json.loads(hero_json(hero)).get("name")
                        return "MISMATCH", f"asked {wanted}: {detail}"
                    return "OK", detail
                if options:
                    o = options[0]
                    need = int((o.get("target_num_range") or [0, 0])[0])
                    targets = list(o.get("all_legal_targets") or [])[:need]
                    answered.append(f"{o.get('name')}{targets}")
                    await self.post(json.dumps({"id": o["id"], "targets": targets, "resources": []}))
            await asyncio.sleep(0.05)
        return "TIMEOUT", f"no mulligan within {budget:.0f}s; answered {answered}; last prompt {prompt[:120]!r}"


async def main(argv):
    global BASE
    hero_fixed = None
    if "--base" in argv:
        i = argv.index("--base")
        BASE = argv[i + 1].rstrip("/")
        argv = argv[:i] + argv[i + 2:]
    if "--hero" in argv:
        i = argv.index("--hero")
        hero_fixed = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    folder = ROOT / "data" / "scenarios"
    files = sorted(p.name for p in folder.glob("*.json"))
    if argv:
        files = [f for f in files if any(a in f for a in argv)]
    results = []
    async with Client() as client:
        for i, f in enumerate(files):
            hero = hero_fixed or HEROES[i % len(HEROES)]
            started = time.time()
            try:
                state, detail = await client.run_one(folder / f, hero)
            except Exception as exc:
                state, detail = "HARNESS", repr(exc)[:300]
            print(f"{state:10} {f:40} {hero:28} {time.time()-started:5.1f}s {detail}", flush=True)
            results.append((state, f, hero, detail))
    bad = [r for r in results if r[0] != "OK"]
    heroes_run = sorted({r[2] for r in results})
    print(f"\n{len(results)} scenario files, {len(heroes_run)}/{len(HEROES)} heroes launched, {len(bad)} not OK")
    for state, f, hero, detail in bad:
        print(f"  {state:8} {f} [{hero}]: {detail[:400]}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
