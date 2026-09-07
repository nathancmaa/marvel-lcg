"""Reading a Marvel Champions Tracker export into game history.

MCT exports an .xlsx, which sounds like it needs a spreadsheet library and does
not: the format is a zip of XML, and a single sheet of plain values is a few
dozen lines of `zipfile` and `ElementTree`. Adding a dependency to the server
for one import screen would be a poor trade.

What this does not do is guess. A row whose hero or scenario cannot be matched
against the catalogue is reported rather than stored under an approximation,
because a game filed against the wrong hero is worse in a coverage grid than a
game that is missing from it.
"""

import re
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence
from xml.etree import ElementTree

SHEET_NAMESPACE = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
_CELL_REFERENCE = re.compile(r'^([A-Z]+)')

# Every column the importer reads. MCT writes more than this -- preplay notes,
# published flags, campaign fields -- which are ignored rather than stored under
# a column that means something else here.
COLUMN_WHEN = 'When?'
COLUMN_OUTCOME = 'Outcome'
COLUMN_DIFFICULTY = 'Difficulty'
COLUMN_HEROIC = 'Heroic Level'
COLUMN_HERO = 'Hero 1'
COLUMN_HERO_ASPECT = 'Hero 1 Aspect'
COLUMN_HERO_DECK = 'Hero 1 Decklist'
COLUMN_SECOND_HERO = 'Hero 2'
COLUMN_SCENARIO = 'Villain / Scenario'
COLUMN_MODULARS = 'Modulars'
COLUMN_NOTES = 'Notes'
COLUMN_RUNTIME = 'Runtime'


def _tag(name: str) -> str:
    return f'{{{SHEET_NAMESPACE}}}{name}'


def ReadSheet(data: bytes) -> List[Dict[str, str]]:
    """The first worksheet as a list of {header: value} rows.

    Values come back as text. Numbers keep their stored form, which is what the
    caller wants for dates written as strings and flags written as 0/1.
    """
    try:
        archive = zipfile.ZipFile(__import__('io').BytesIO(data))
    except zipfile.BadZipFile as error:
        raise ValueError('That file is not an .xlsx workbook.') from error

    names = archive.namelist()
    if 'xl/worksheets/sheet1.xml' not in names:
        raise ValueError('The workbook has no first worksheet.')

    shared: List[str] = []
    if 'xl/sharedStrings.xml' in names:
        root = ElementTree.fromstring(archive.read('xl/sharedStrings.xml'))
        for item in root.findall(_tag('si')):
            shared.append(''.join(node.text or '' for node in item.iter(_tag('t'))))

    sheet = ElementTree.fromstring(archive.read('xl/worksheets/sheet1.xml'))
    rows: List[Dict[str, str]] = []
    for row in sheet.iter(_tag('row')):
        cells: Dict[str, str] = {}
        for cell in row.findall(_tag('c')):
            reference = cell.get('r') or ''
            match = _CELL_REFERENCE.match(reference)
            if not match:
                continue
            value = cell.find(_tag('v'))
            if value is None or value.text is None:
                text = ''
            elif cell.get('t') == 's':
                index = int(value.text)
                text = shared[index] if 0 <= index < len(shared) else ''
            else:
                text = value.text
            cells[match.group(1)] = text
        rows.append(cells)

    if not rows:
        return []

    header = rows[0]
    return [
        {header.get(column, column): value for column, value in row.items()}
        for row in rows[1:]
    ]


def Slug(value: str) -> str:
    value = str(value).strip().lower().replace('&', ' and ')
    return re.sub(r'[^a-z0-9]+', '_', value).strip('_')


def _match_key(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', str(value).lower())


def ParseWhen(value: str) -> str:
    """MCT writes `MM/DD/YY HH:MM:SS`; anything else is left to the caller."""
    text = str(value).strip()
    if not text:
        raise ValueError('The row has no date.')
    for pattern in ('%m/%d/%y %H:%M:%S', '%m/%d/%Y %H:%M:%S',
                    '%Y-%m-%d %H:%M:%S', '%m/%d/%y %H:%M', '%m/%d/%Y %H:%M'):
        try:
            stamp = datetime.strptime(text, pattern)
        except ValueError:
            continue
        return stamp.replace(tzinfo=timezone.utc).isoformat()
    raise ValueError(f'Unrecognised date: {text}')


class TrackerImport:
    """Turns exported rows into records `GameHistory._store_game` accepts."""

    def __init__(
        self,
        heroes: Sequence[Dict[str, str]],
        scenarios: Sequence[Dict[str, str]],
    ) -> None:
        # Heroes are matched on the display name and, where two share one, on
        # the disambiguated form MCT also uses: "Black Panther (Shuri)".
        self.heroes: Dict[str, Dict[str, str]] = {}
        self.heroes_by_name: Dict[str, List[Dict[str, str]]] = {}
        for hero in heroes:
            for label in (hero.get('name', ''), hero.get('label', '')):
                key = _match_key(label)
                if key:
                    self.heroes.setdefault(key, hero)
            self.heroes_by_name.setdefault(
                _match_key(hero.get('name', '')), []).append(hero)
        self.scenarios: Dict[str, Dict[str, str]] = {}
        for scenario in scenarios:
            key = _match_key(scenario.get('name', ''))
            if key:
                self.scenarios.setdefault(key, scenario)

    def HeroFor(self, raw: str) -> Optional[Dict[str, str]]:
        """Match a tracker's hero name, including its way of disambiguating.

        Where two heroes share a name, this build labels only the newcomer --
        "Spider-Man" and "Spider-Man (Miles Morales)" -- while a tracker labels
        both, so an export says "Spider-Man (Peter Parker)" for the one with no
        label here. A qualifier that names no variant is therefore taken to
        mean the original: the hero whose file is the bare name.
        """
        hero = self.heroes.get(_match_key(raw))
        if hero is not None:
            return hero

        match = re.match(r'^(.*?)\s*\(([^)]*)\)\s*$', str(raw).strip())
        if not match:
            return None
        base, qualifier = match.group(1), match.group(2)
        candidates = self.heroes_by_name.get(_match_key(base), [])
        if not candidates:
            return None

        wanted = _match_key(qualifier)
        for candidate in candidates:
            if wanted and wanted in _match_key(candidate.get('id', '')):
                return candidate
        for candidate in candidates:
            if _match_key(candidate.get('id', '')) == _match_key(base):
                return candidate
        return candidates[0] if len(candidates) == 1 else None

    def Convert(self, row: Dict[str, str], source: str) -> Dict[str, Any]:
        """One exported row as a history record.

        Raises ValueError with a readable reason when the row cannot be filed,
        which the caller collects and reports rather than swallowing.
        """
        hero_name = str(row.get(COLUMN_HERO, '')).strip()
        scenario_name = str(row.get(COLUMN_SCENARIO, '')).strip()
        if not hero_name or not scenario_name:
            raise ValueError('The row names no hero or no scenario.')

        hero = self.HeroFor(hero_name)
        if hero is None:
            raise ValueError(f'No hero called "{hero_name}"')
        scenario = self.scenarios.get(_match_key(scenario_name))
        if scenario is None:
            raise ValueError(f'No scenario called "{scenario_name}"')

        finished_at = ParseWhen(row.get(COLUMN_WHEN, ''))
        outcome = str(row.get(COLUMN_OUTCOME, '')).strip().lower()
        result = {'win': 'win', 'loss': 'loss', 'lose': 'loss'}.get(outcome, 'unknown')
        expert = str(row.get(COLUMN_DIFFICULTY, '')).strip().lower() == 'expert'

        # Kept as notes rather than dropped: this build has no Heroic mode and
        # no second-hero column, and losing either silently would misreport what
        # the game actually was.
        remarks: List[str] = []
        heroic = str(row.get(COLUMN_HEROIC, '')).strip()
        if heroic and heroic.lower() not in ('none', '0'):
            remarks.append(f'Heroic {heroic}')
        second = str(row.get(COLUMN_SECOND_HERO, '')).strip()
        if second:
            remarks.append(f'Two-hero game, also played {second}')
        aspect = str(row.get(COLUMN_HERO_ASPECT, '')).strip()
        if aspect:
            remarks.append(aspect)
        modulars = str(row.get(COLUMN_MODULARS, '')).strip()
        if modulars:
            remarks.append(f'Modulars: {modulars}')
        notes = str(row.get(COLUMN_NOTES, '')).strip()
        if notes:
            remarks.append(notes)

        scenario_key = Slug(scenario['name'])
        return {
            # Stable across re-imports of the same export, which is what makes
            # `INSERT OR IGNORE` on source_key the whole of the deduplication.
            'source_key': f'mct:{finished_at}:{hero["code"]}:{scenario_key}',
            'finished_at': finished_at,
            'rules_version': 'v18',
            'hero_code': hero['code'],
            'hero_name': hero.get('name', hero_name),
            'villain_name': scenario['name'],
            'scenario_name': scenario['name'],
            'scenario_key': scenario_key,
            'expert': int(expert),
            'result': result,
            'game_mode': 'physical' if source == 'physical' else 'quick',
            'deck_name': str(row.get(COLUMN_HERO_DECK, '')).strip()[:200],
            'deck_source': 'mct',
            'source': source,
            'notes': ' · '.join(remarks)[:4000],
        }
