"""Telling apart heroes that share a name.

Two Black Panthers are in the game -- T'Challa's core-set hero and Shuri's
pack -- and two Spider-Men, Peter Parker and Miles Morales. The history keeps
them apart by hero code, so their records never mix, but a card is named only
"Black Panther", and so was every row and axis that showed one. The label
here adds the alter ego where, and only where, the name alone does not say
which hero it is: "Black Panther (Shuri)". Ant-Man's second identity card is
still Scott Lang, so Ant-Man stays Ant-Man.
"""
from __future__ import annotations

from typing import Dict, Optional, Set

_alter_egos: Dict[str, str] = {}
_shared_names: Set[str] = set()
_loaded = False


def _clean(name: str) -> str:
    return name.replace('* ', '').strip()


def _load() -> None:
    global _loaded
    if _loaded:
        return
    _loaded = True
    try:
        from cards.database import CardsDB
        papers = CardsDB.papers
    except Exception:
        return
    egos_by_name: Dict[str, Set[str]] = {}
    for code, paper in papers.items():
        if getattr(paper, 'type', '') != 'Hero' or not code.endswith('a'):
            continue
        back = papers.get(code[:-1] + 'b')
        alter_ego = _clean(getattr(back, 'name', '') or '') if back else ''
        if not alter_ego:
            continue
        _alter_egos[code.lower()] = alter_ego
        egos_by_name.setdefault(_clean(paper.name), set()).add(alter_ego)
    _shared_names.update(name for name, egos in egos_by_name.items() if len(egos) > 1)


def Reset() -> None:
    """Forget what was read, so a test can load different cards."""
    global _loaded
    _loaded = False
    _alter_egos.clear()
    _shared_names.clear()


def HeroLabel(code: Optional[str], name: Optional[str]) -> str:
    """The hero's name, with the alter ego added when the name is shared."""
    name = _clean(name or '')
    if not name or not code:
        return name
    _load()
    if name not in _shared_names:
        return name
    alter_ego = _alter_egos.get(str(code).strip().lower())
    if not alter_ego or name.endswith(f'({alter_ego})'):
        return name
    return f'{name} ({alter_ego})'
