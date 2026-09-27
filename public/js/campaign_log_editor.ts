/**
 * The between-scenario campaign log editor on the solo Campaign page.
 *
 * Most boxes record choices and outcomes the engine cannot see (a role
 * upgrade bought, a pool card earned, a mission failed), so between
 * scenarios the player writes them down here, as they would on the paper
 * log. The saved log is the server's campaign record; this editor only
 * shows the fields that matter to a one-hero game of the chosen campaign.
 *
 * Keys are the engine's campaign log keys (CampaignLog in
 * game/operate/campaign_logs.py); the server refuses any other.
 */
import { withCardImageRevision } from './card_image_url.js';

type FieldType = 'number' | 'yes' | 'select' | 'multi' | 'text';

export type CampaignLogField = {
    key: string;
    label?: string;
    type: FieldType;
    options?: string[];
    hint?: string;
    /** Shown only in an expert campaign. */
    expertOnly?: boolean;
};

const range = (first: number, count: number): string[] =>
    Array.from({length: count}, (_, index) => String(first + index));

const hitPoints: CampaignLogField = {
    key: 'Player 1 Remaining hit points',
    label: 'Remaining hit points',
    type: 'number',
    hint: '0 means your hero was defeated.',
    expertOnly: true,
};

const shieldTech = ['27182a,27182b', '27183a,27183b', '27184a,27184b', '27185a,27185b',
    '27186a,27186b', '27187a,27187b', '27188a,27188b', '27189a,27189b'];

export const campaignLogFields: Record<string, CampaignLogField[]> = {
    rise_of_red_skull: [
        hitPoints,
        {key: 'Player 1 Tech Upgrade', label: 'Tech upgrade', type: 'select', options: ['04155', '04156', '04157', '04158']},
        {key: 'Player 1 tech upgrade removed from campaign', label: 'Tech upgrade removed from the campaign', type: 'yes'},
        {key: 'Player 1 Basic Upgrade', label: 'Basic upgrade', type: 'select',
            options: ['04159a', '04160a', '04161a', '04162a']},
        {key: 'Player 1 Basic Condition replaced with Improved side', label: 'Basic condition replaced with its Improved side', type: 'yes'},
        {key: 'Player 1 Obligations', label: 'Obligations', type: 'multi', options: ['04163', '04164', '04165', '04166']},
        {key: 'Player 1 Rescued Allies', label: 'Rescued allies', type: 'multi', options: ['04097', '04098', '04099', '04100']},
        {key: 'Experimental Weapons added to encounter deck', type: 'multi', options: ['04072', '04073', '04074', '04075']},
        {key: 'Number of delay counters on main scheme', type: 'number'},
        {key: 'Allies removed from the campaign', type: 'text', hint: "Card IDs separated by ';'"},
    ],
    galaxys_most_wanted: [
        hitPoints,
        {key: 'Player 1 Unspent Units', label: 'Unspent units', type: 'number'},
        {key: 'Player 1 Market Cards', label: 'Market cards', type: 'multi', options: range(16150, 28)},
        {key: 'Player 1 Cards in The Collection', label: 'Cards in The Collection', type: 'text', hint: "Card IDs separated by ';'"},
        {key: 'Headhunter Defeated', type: 'multi', options: ['Scenario 1', 'Scenario 2', 'Scenario 3', 'Scenario 4']},
        {key: 'Galactic Artifacts Side Schemes in the Victory Display', type: 'multi', options: ['16127', '16128', '16129', '16130']},
        {key: 'Power Stone Control', type: 'yes', hint: 'You control the Power Stone.', options: ['Player 1']},
        {key: 'Evasion Counters', type: 'number'},
        {key: 'Reveal Kree Supremacy', type: 'yes'},
    ],
    mad_titans_shadow: [
        hitPoints,
        {key: 'Cosmo in campaign pool', type: 'yes'},
        {key: 'Security Breach in campaign pool', type: 'yes'},
        {key: 'Shawarma in campaign pool', type: 'yes'},
        {key: 'Black Swan in campaign pool', type: 'yes'},
        {key: 'Avengers Tower has the Damaged trait', type: 'yes'},
        {key: 'System Shock in campaign pool', type: 'yes'},
        {key: 'The Infinity Stones 1B was completed', type: 'yes'},
        {key: 'Norn Stone in campaign pool', type: 'yes'},
        {key: 'Odin in campaign pool', type: 'yes'},
    ],
    sinister_motives: [
        hitPoints,
        {key: 'Reputation Track', type: 'number'},
        {key: 'Community Service: Victory for Scenarios #1-4', type: 'multi', options: ['27176', '27177', '27178', '27179', '27180']},
        {key: 'Waking Nightmare: Victory for Scenario #3 - Mysterio', type: 'number'},
        {key: 'Last Ones Standing: Victory for Scenario #4 - The Sinister Six', type: 'multi',
            options: ['27099', '27094', '27095', '27096', '27097', '27098']},
        {key: 'S.H.I.E.L.D. Tech: Reputation Track Reward P1', label: 'S.H.I.E.L.D. Tech reward', type: 'select', options: shieldTech},
        {key: 'Aspect Advantage: Reputation Track Reward P1', label: 'Aspect Advantage reward', type: 'text',
            hint: "Card IDs separated by ';', e.g. 05015;05015;05015"},
        {key: 'Planning Ahead: Reputation Track Reward P1', label: 'Planning Ahead reward', type: 'text', hint: 'One card ID'},
        {key: 'Osborn Tech: Reputation Track Penalty', type: 'multi', options: ['27147', '27148', '27149', '27150', '27151', '27152']},
    ],
    mutant_genesis: [
        hitPoints,
        {key: 'Player 1 Role', label: 'Role', type: 'select', options: ['Brawler', 'Commander', 'Defender', 'Peacekeeper']},
        {key: 'Frightened Police Defeated', type: 'yes'},
        {key: 'Enemy of My Enemy Defeated', type: 'yes'},
        {key: 'Find the Prisoners Defeated', type: 'yes'},
        {key: 'Surprise Attack Defeated', type: 'yes'},
        {key: 'Future Past Cards in Encounter Deck', type: 'multi', options: range(32166, 5)},
        {key: 'Future Past Cards removed from campaign', type: 'multi', options: range(32166, 5)},
        {key: 'Role Upgrades removed from campaign', type: 'multi', options: range(32176, 20)},
        {key: 'Jubilee', type: 'select', options: ['32088b']},
        {key: 'Player 1 Captive Allies', label: 'Captive allies', type: 'multi', options: ['32089', '32090', '32091', '32092']},
        {key: 'Allies removed from the campaign', type: 'text', hint: "Card IDs separated by ';'"},
    ],
    next_evolution: [
        hitPoints,
        {key: 'Marauders Defeated', type: 'multi', options: ['40070a', '40071a', '40072a', '40073a', '40074a', '40075a', '40076a']},
        {key: 'Morlocks Saved', type: 'number'},
        ...[1, 2, 3, 4, 5].map((scenario): CampaignLogField => ({
            key: `Scenario ${scenario} Player Side Scheme`,
            type: 'select',
            options: ['40190a', '40191a', '40192a', '40193a', '40194a', '40195a'],
        })),
        {key: 'Campaign Environments Earned', type: 'multi', options: ['40190b', '40191b', '40192b', '40193b', '40194b', '40195b']},
        {key: 'Scenario 3 Hope Summers Damage', type: 'number'},
        {key: 'Scenario 4 Hope Summers Damage', type: 'number'},
    ],
    age_of_apocalypse: [
        hitPoints,
        {key: 'Mission Side Schemes Removed from campaign', type: 'multi', options: ['45166a', '45167a', '45168a', '45169a']},
        {key: 'Mission Side Schemes Defeated', type: 'multi', options: ['45166a', '45167a', '45168a', '45169a'],
            hint: 'A defeated mission is also marked removed above.'},
        {key: 'Overseers Defeated', type: 'multi', options: ['45179a', '45180a', '45181a', '45182a', '45183a']},
        {key: 'Player 1 Campaign Ally', label: 'Campaign ally', type: 'select', options: ['45172', '45173', '45174', '45175']},
        {key: 'Player 1 Campaign Aspect Upgrade', label: 'Campaign aspect upgrade', type: 'text', hint: 'One card ID'},
        {key: 'Player 1 Campaign Aspect Support', label: 'Campaign aspect support', type: 'text', hint: 'One card ID'},
    ],
    agents_of_shield: [
        // Evidence, board flips and secret counters are recorded by the game
        // itself; the seed that decides the evidence is never shown.
        hitPoints,
        {key: 'Evidence Earned', type: 'multi', options: range(50185, 9)},
        {key: 'Scenario 1 Minions and side schemes in play', type: 'number'},
        {key: 'Scenario 2 Rescued Captives', type: 'number'},
        {key: 'Scenario 3 Adaptoid environments', type: 'multi', options: ['50109', '50110', '50111', '50112']},
        {key: 'Scenario 4 Surviving Thunderbolts', type: 'multi', options: ['50139', '50143', '50148', '50152', '50156', '50161']},
    ],
};

/** A field about scenario N matters once scenario N is current or done. */
function isRelevant(field: CampaignLogField, scenarioIndex: number, expert: boolean): boolean {
    if (field.expertOnly && !expert) {
        return false;
    }
    const scenario = /^Scenario (\d)\b/.exec(field.key);
    return !scenario || Number(scenario[1]) <= scenarioIndex + 1;
}

export function relevantCampaignLogFields(
    campaignId: string,
    scenarioIndex: number,
    expert: boolean,
): CampaignLogField[] {
    return (campaignLogFields[campaignId] ?? [])
        .filter((field) => isRelevant(field, scenarioIndex, expert));
}

function looksLikeCardId(value: string): boolean {
    return /^\d{5}[a-z]?$/.test(value.split(',')[0] ?? '');
}

const cardNames = new Map<string, Promise<string>>();

function cardName(cardId: string): Promise<string> {
    const id = cardId.split(',')[0] ?? cardId;
    let name = cardNames.get(id);
    if (!name) {
        name = fetch(`/get_card_json?${encodeURIComponent(id)}`)
            .then(async (response) => response.ok
                ? String((await response.json() as {name?: string}).name ?? id)
                : id)
            .catch(() => id);
        cardNames.set(id, name);
    }
    return name;
}

function createOption(
    inputType: 'radio' | 'checkbox',
    groupName: string,
    value: string,
    checked: boolean,
): HTMLLabelElement {
    const label = document.createElement('label');
    label.className = 'log-option';
    const input = document.createElement('input');
    input.type = inputType;
    input.name = groupName;
    input.value = value;
    input.checked = checked;
    label.append(input);

    if (looksLikeCardId(value)) {
        label.classList.add('log-card-option');
        const image = document.createElement('img');
        image.src = withCardImageRevision(`/${value.split(',')[0]}`);
        image.alt = '';
        image.loading = 'lazy';
        const caption = document.createElement('span');
        caption.textContent = value.split(',')[0] ?? value;
        void cardName(value).then((name) => {
            caption.textContent = name;
            label.title = value;
        });
        label.append(image, caption);
    } else {
        const caption = document.createElement('span');
        caption.textContent = value;
        label.append(caption);
    }
    return label;
}

export type CampaignLogEditor = {
    /** The full log to save: the edited fields over every other entry. */
    read(): Record<string, string>;
};

let editorCount = 0;

/**
 * Draw the editor into ``host`` and return a reader for the edited log.
 * Entries the editor does not show are kept as they were.
 */
export function renderCampaignLogEditor(
    host: HTMLElement,
    campaignId: string,
    scenarioIndex: number,
    expert: boolean,
    log: Record<string, string>,
): CampaignLogEditor {
    const fields = relevantCampaignLogFields(campaignId, scenarioIndex, expert);
    const prefix = `campaign-log-${++editorCount}`;
    const readers: Array<() => [string, string]> = [];
    host.replaceChildren();

    fields.forEach((field, index) => {
        const current = log[field.key] ?? '';
        const group = document.createElement('fieldset');
        group.className = `log-field log-field-${field.type}`;
        const legend = document.createElement('legend');
        legend.textContent = field.label ?? field.key;
        group.append(legend);
        const groupName = `${prefix}-${index}`;

        if (field.type === 'number' || field.type === 'text') {
            const input = document.createElement('input');
            input.type = field.type === 'number' ? 'number' : 'text';
            if (field.type === 'number') {
                input.inputMode = 'numeric';
                input.min = '0';
                input.step = '1';
            } else {
                input.autocomplete = 'off';
                input.spellcheck = false;
            }
            input.value = current;
            input.placeholder = field.hint ?? '';
            input.setAttribute('aria-label', field.label ?? field.key);
            group.append(input);
            readers.push(() => [field.key, input.value.trim()]);
        } else if (field.type === 'yes') {
            const yesValue = field.options?.[0] ?? 'Yes';
            const label = document.createElement('label');
            label.className = 'log-toggle';
            const input = document.createElement('input');
            input.type = 'checkbox';
            input.checked = current !== '';
            const caption = document.createElement('span');
            caption.textContent = field.hint ?? 'Yes';
            label.append(input, caption);
            group.append(label);
            readers.push(() => [field.key, input.checked ? yesValue : '']);
        } else {
            const selected = new Set(current.split(';').filter(Boolean));
            const options = document.createElement('div');
            options.className = 'log-options';
            const inputType = field.type === 'select' ? 'radio' : 'checkbox';
            if (field.type === 'select') {
                options.append(createOption('radio', groupName, '', current === ''));
                const none = options.lastElementChild?.querySelector('span');
                if (none) {
                    none.textContent = 'None';
                }
            }
            // A recorded value this list does not offer is shown too, so
            // saving never drops it.
            const values = [...(field.options ?? [])];
            for (const value of selected) {
                if (!values.includes(value)) {
                    values.push(value);
                }
            }
            if (field.type === 'select' && current && !values.includes(current)) {
                values.push(current);
            }
            for (const option of values) {
                const isChecked = field.type === 'select' ? option === current : selected.has(option);
                options.append(createOption(inputType, groupName, option, isChecked));
            }
            group.append(options);
            readers.push(() => {
                const checked = [...options.querySelectorAll<HTMLInputElement>('input:checked')]
                    .map((input) => input.value)
                    .filter(Boolean);
                return [field.key, checked.join(';')];
            });
        }
        if (field.hint && field.type !== 'yes' && field.type !== 'text') {
            const hint = document.createElement('small');
            hint.textContent = field.hint;
            group.append(hint);
        }
        host.append(group);
    });

    if (!fields.length) {
        const empty = document.createElement('p');
        empty.className = 'load-status';
        empty.textContent = 'This campaign records nothing by hand at this point.';
        host.append(empty);
    }

    return {
        read(): Record<string, string> {
            const result: Record<string, string> = {...log};
            for (const reader of readers) {
                const [key, value] = reader();
                if (value) {
                    result[key] = value;
                } else {
                    delete result[key];
                }
            }
            return result;
        },
    };
}
