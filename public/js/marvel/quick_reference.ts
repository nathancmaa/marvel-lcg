// The keywords and icons the game puts on the board, and what they do.
//
// The wording is the official reference's, verbatim, rather than a paraphrase:
// a rules reference that is nearly right is worse than none, and these are
// short enough that saying them differently only risks saying them wrong.
//
// The icons are the ones the app already draws for card text, so a row shows
// the same mark you are looking at on the table rather than a picture of one.

type Entry = {
    name: string;
    /** The app's own icon class, where it draws one. */
    icon?: string;
    text: string;
};

const KEYWORDS: readonly Entry[] = [
    {name: 'Alliance', text: 'When a player declares their intention to play an alliance card, any player(s) may help pay the costs for that card.'},
    {name: 'Form', text: 'A card with the form keyword grants an identity a unique form.'},
    {name: 'Guard', text: 'While a minion with guard is engaged with a player, that player cannot attack the villain.'},
    {name: 'Hinder X', text: 'When a player reveals a card with hinder X, that player places X threat on that card.'},
    {name: 'Incite X', text: 'When a player reveals a card with incite X, that player places X threat on the main scheme.'},
    {name: 'Overkill', text: 'Excess damage from attacks with overkill are dealt to the identity or villain.'},
    {name: 'Patrol', text: 'While a minion with patrol is engaged with a player, that player cannot thwart the main scheme.'},
    {name: 'Peril', text: 'While a player is resolving a card with peril, other players cannot help that player.'},
    {name: 'Permanent', text: 'Cards with permanent cannot leave play.'},
    {name: 'Piercing', text: 'Attacks with piercing discard tough status cards from the attacked character before damage is dealt.'},
    {name: 'Quickstrike', text: 'After this enemy engages a player, it immediately attacks that player if they are in hero form.'},
    {name: 'Ranged', text: 'Attacks with ranged ignore retaliate.'},
    {name: 'Requirement (Resources)', text: "A card with the requirement keyword cannot be played unless each resource of the specified type is spent while paying for that card's cost."},
    {name: 'Restricted', text: 'A player cannot control more than two restricted cards at a given time.'},
    {name: 'Retaliate X', text: 'After a character with retaliate X is attacked, deal X damage to the attacker.'},
    {name: 'Setup', text: 'Cards with setup start the game in play.'},
    {name: 'Stalwart', text: 'Characters with Stalwart cannot be stunned or confused.'},
    {name: 'Steady', text: 'A character with the steady keyword is not stunned or confused unless it has two stunned or confused status cards, respectively.'},
    {name: 'Surge', text: 'After a player reveals a card with surge, that player reveals an additional encounter card.'},
    {name: 'Team-Up', text: 'Cards with team-up cannot be played unless both characters listed by the keyword are in play.'},
    {name: 'Teamwork (TRAIT)', text: 'After a minion with teamwork enters play and engages a player, if there is at least one other minion that shares the specified trait in play, each minion that shares the teamwork keyword with the same specified trait activates against the player it is engaged with.'},
    {name: 'Temporary', text: 'A card with temporary must be discarded from play at the end of the round.'},
    {name: 'Toughness', text: 'When a character with toughness enters play, place a tough status card on it.'},
    {name: 'Uses (X "type")', text: 'When a card with uses enters play, place X all-purpose counters from the token pool on that card. After the last all-purpose counter is removed from a card with uses (and the effect resolves), discard that card.'},
    {name: 'Victory X', text: 'When a card with victory X is defeated, add it to the victory display.'},
    {name: 'Villainous', text: 'When a minion with villainous activates, give it a boost card.'},
];

const ICONS: readonly Entry[] = [
    {name: 'Energy', icon: 'energy', text: 'An energy icon is a resource icon that generates one energy resource when spent.'},
    {name: 'Mental', icon: 'mental', text: 'A mental icon is a resource icon that generates one mental resource when spent.'},
    {name: 'Physical', icon: 'physical', text: 'A physical icon is a resource icon that generates one physical resource when spent.'},
    {name: 'Wild', icon: 'wild', text: 'A wild icon is a resource icon that can generate one energy, mental, physical, or wild resource when spent.'},
    {name: 'Acceleration', icon: 'acceleration', text: 'An acceleration icon places additional threat on the main scheme during the villain phase.'},
    {name: 'Amplify', icon: 'amplify', text: 'An amplify icon increases the number of boost icons on boost cards during enemy activations by one.'},
    {name: 'Crisis', icon: 'crisis', text: 'A crisis icon prevents players from removing threat from the main scheme.'},
    {name: 'Hazard', icon: 'hazard', text: 'A hazard icon increases the number of encounter cards that are dealt to players during the villain phase. Each hazard icon deals one player one additional card (not one card per player).'},
    {name: 'Boost', icon: 'boost', text: "A boost icon increases the activating enemy's ATK or SCH value during enemy activations."},
    // The only one the app has no mark of its own for, so it is named and not
    // drawn rather than drawn wrongly.
    {name: 'Star', text: "A star icon is used in conjunction with a card's stat or boost field to indicate that there is a mandatory ability in the text box that corresponds to that field."},
    {name: 'Consequential Damage', icon: 'consequential', text: "A consequential damage icon is used in conjunction with an ally's ATK field or THW field. After an ally attacks or thwarts, it takes one consequential damage for each consequential damage icon in that field."},
    {name: 'Per Player', icon: 'per_hero', text: 'A per player icon next to a value multiplies that value by the number of players who started the scenario.'},
    {name: 'Unique', icon: 'unique', text: "A unique icon in a card's title indicates the card is unique."},
];

export class QuickReference {
    private static panel = document.getElementById('quick-reference') as HTMLElement | null;
    private static body = document.getElementById('quick-reference-body') as HTMLElement | null;
    private static filter = document.getElementById('quick-reference-filter') as HTMLInputElement | null;
    private static built = false;

    static toggle(): void {
        QuickReference.panel?.classList.toggle('hide');
        if( QuickReference.isOpen() ) {
            QuickReference.build();
            QuickReference.filter?.focus();
        }
    }

    static close(): void {
        QuickReference.panel?.classList.add('hide');
    }

    static isOpen(): boolean {
        return QuickReference.panel !== null
            && !QuickReference.panel.classList.contains('hide');
    }

    private static row(entry: Entry): HTMLElement {
        const row = document.createElement('li');
        row.className = 'reference-row';
        // Matched against the whole row rather than the name, so "threat"
        // finds the icons that place it as well as the keywords that name it.
        row.dataset.search = `${entry.name} ${entry.text}`.toLowerCase();

        const head = document.createElement('span');
        head.className = 'reference-name';
        if( entry.icon ) {
            const mark = document.createElement('span');
            mark.className = `icon-${entry.icon} reference-icon`;
            head.appendChild(mark);
        }
        head.append(entry.name);

        const text = document.createElement('span');
        text.className = 'reference-text';
        text.textContent = entry.text;

        row.append(head, text);
        return row;
    }

    private static section(title: string, entries: readonly Entry[]): HTMLElement {
        const section = document.createElement('section');
        section.className = 'reference-section';

        const heading = document.createElement('h3');
        heading.textContent = title;

        const list = document.createElement('ul');
        list.className = 'reference-list';
        list.append(...entries.map(QuickReference.row));

        section.append(heading, list);
        return section;
    }

    /** Built once, on first open: it is the same list every game. */
    private static build(): void {
        if( QuickReference.built || !QuickReference.body ) {
            return;
        }
        QuickReference.body.replaceChildren(
            QuickReference.section('Keywords', KEYWORDS),
            QuickReference.section('Icons', ICONS),
        );
        QuickReference.built = true;
    }

    private static applyFilter(): void {
        const wanted = (QuickReference.filter?.value ?? '').trim().toLowerCase();
        for( const section of QuickReference.body?.querySelectorAll<HTMLElement>('.reference-section') ?? [] ) {
            let shown = 0;
            for( const row of section.querySelectorAll<HTMLElement>('.reference-row') ) {
                const hit = !wanted || (row.dataset.search ?? '').includes(wanted);
                row.hidden = !hit;
                if( hit ) {
                    shown += 1;
                }
            }
            // A heading over nothing reads as a section with no entries rather
            // than as a section that does not match.
            section.hidden = shown === 0;
        }
    }

    static bind(): void {
        const close = document.getElementById('quick-reference-close');
        close?.addEventListener('click', () => QuickReference.close());
        close?.addEventListener('keydown', (event) => {
            if( (event as KeyboardEvent).key === 'Enter' ) {
                QuickReference.close();
            }
        });
        QuickReference.filter?.addEventListener('input', () => QuickReference.applyFilter());
    }
}

QuickReference.bind();
