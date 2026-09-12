"""A play file for BG Stats, holding every decided game at once.

BG Stats imports the same JSON it exports: separate arrays of games, players,
locations and plays, each object numbered within the file and referenced by
that number, plus a UUID by which the app recognises the object across
imports. The shape here follows the app's own example export, field for
field, because the import is strict and says nothing about why a file was
refused. The deep link the history page also offers carries one play; this
carries all of them.

The UUIDs are derived, not random: the same game, player, location or play
always gets the same one, so a second import matches what the first one
created instead of asking again -- and so a play imported twice is one play.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Sequence
import uuid

# Marvel Champions: The Card Game on BoardGameGeek.
MARVEL_CHAMPIONS_BGG_ID = 285774
MARVEL_CHAMPIONS_NAME = 'Marvel Champions: The Card Game'
MARVEL_CHAMPIONS_YEAR = 2019

# Where the plays are filed when no location is set. The deep link's docs
# say BG Stats falls back to the source name on its own; the app does not,
# and files them under "No location", so the name goes in explicitly.
DEFAULT_LOCATION = 'Marvel Champions Digital'

# BG Stats' own separator for several roles or boards in one field. Not a
# slash: a fullwidth solidus, which the app splits on.
ROLE_SEPARATOR = '／'

# Everything this file names is derived under one namespace, so nothing here
# can collide with a UUID BG Stats made for itself.
_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, 'https://github.com/nathancmaa/marvel-lcg/bgstats')


def _stable_uuid(key: str) -> str:
    # Upper case, which is how the app writes its own.
    return str(uuid.uuid5(_NAMESPACE, key)).upper()


def _bgstats_time(value: Any) -> str:
    """The app's own timestamp: UTC, `yyyy-MM-dd HH:mm:ss`."""
    if isinstance(value, datetime):
        when = value
    else:
        text = str(value or '').strip().replace('Z', '+00:00')
        try:
            when = datetime.fromisoformat(text)
        except ValueError:
            return ''
    if when.tzinfo is not None:
        when = when.astimezone(timezone.utc)
    return when.strftime('%Y-%m-%d %H:%M:%S')


def _comments(game: Mapping[str, Any]) -> str:
    parts: List[str] = []
    if game.get('heroic'):
        parts.append(f"Heroic {game['heroic']}")
    parts.append('Expert' if game.get('expert') else 'Standard')
    rounds = game.get('rounds')
    if rounds:
        parts.append(f"{rounds} round{'' if rounds == 1 else 's'}")
    if (game.get('seats') or 0) > 1:
        parts.append(f"{game['seats']}-handed")
    decks = str(game.get('decks') or '').strip()
    for text in (decks.split(ROLE_SEPARATOR) if decks else [str(game.get('deck_name') or '')]):
        text = text.strip()
        if text:
            parts.append(text)
    notes = str(game.get('notes') or '').strip()
    if notes:
        parts.append(notes)
    return ' · '.join(parts)


def _role(game: Mapping[str, Any]) -> str:
    """The hero, or every hero in seat order for a two-handed game."""
    heroes = str(game.get('heroes') or '').strip()
    return heroes or str(game.get('hero_name') or '')


def BuildBgStatsFile(games: Sequence[Mapping[str, Any]],
                     player_name: str,
                     location: str = '',
                     now: datetime | None = None) -> Dict[str, Any]:
    """The file's content, as the object to serialise.

    `games` are history rows: id, finished_at, hero_name, villain_name,
    result, rounds, playtime_seconds, expert, heroic, deck_name, notes.
    Only decided games belong here; the caller filters, since an abandoned
    game would arrive in BG Stats as a loss.
    """
    stamp = _bgstats_time(now or datetime.now(timezone.utc))
    player_name = player_name.strip() or 'Me'
    location = location.strip() or DEFAULT_LOCATION

    game_ref = 1
    player_ref = 1
    location_ref = 1

    plays: List[Dict[str, Any]] = []
    for game in games:
        played = _bgstats_time(game.get('finished_at'))
        play: Dict[str, Any] = {
            'uuid': _stable_uuid(f"play:{game['id']}"),
            'ignored': False,
            'rating': 0,
            'scoringSetting': 0,
            'manualWinner': False,
            'usesTeams': False,
            'bggId': 0,
            'nemestatsId': 0,
            'playImages': '[]',
            'playDate': played,
            'entryDate': played,
            'modificationDate': stamp,
            'rounds': int(game.get('rounds') or 0),
            'comments': _comments(game),
            # The board or variant: the scenario, as the deep link sends it.
            'board': str(game.get('villain_name') or ''),
            'gameRefId': game_ref,
            'playerScores': [{
                'playerRefId': player_ref,
                'winner': game.get('result') == 'win',
                'startPlayer': True,
                'seatOrder': 0,
                'rank': 0,
                'score': '',
                'newPlayer': False,
                # What the player was in the play: the hero, or both.
                'role': _role(game),
            }],
        }
        play['locationRefId'] = location_ref
        seconds = game.get('playtime_seconds')
        if seconds:
            # Half up, as the deep link rounds it, not to even.
            minutes = int(seconds // 60) + (1 if seconds % 60 >= 30 else 0)
            if minutes > 0:
                play['durationMin'] = minutes
        plays.append(play)

    content: Dict[str, Any] = {
        'games': [{
            'id': game_ref,
            'uuid': _stable_uuid('game:marvel-champions'),
            'name': MARVEL_CHAMPIONS_NAME,
            'bggId': MARVEL_CHAMPIONS_BGG_ID,
            'bggName': MARVEL_CHAMPIONS_NAME,
            'bggYear': MARVEL_CHAMPIONS_YEAR,
            # A win or a loss against the villain, never a score.
            'noPoints': True,
            'highestWins': True,
            'cooperative': True,
            'usesTeams': False,
            'modificationDate': stamp,
        }],
        'players': [{
            'id': player_ref,
            'uuid': _stable_uuid('player:marvel-champions-digital-player'),
            'name': player_name,
            'isAnonymous': False,
            'modificationDate': stamp,
        }],
        'locations': [{
            'id': location_ref,
            'uuid': _stable_uuid(f"location:{location.casefold()}"),
            'name': location,
            'modificationDate': stamp,
        }],
        'plays': plays,
        'userInfo': {'meRefId': player_ref},
        'challenges': [],
    }
    return content
