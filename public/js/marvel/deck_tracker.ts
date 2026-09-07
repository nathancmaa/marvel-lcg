// What is left in your deck, and what has already come out.
//
// The engine sends the player deck to the client with real card ids and in
// real order, because a solo game trusts its own client. That means the order
// is available here and is deliberately never shown: the list is sorted by
// cost, the way a decklist is written, so it tells you what remains without
// telling you what is on top.
//
// Counts come from the deck itself, so "remaining" is exact. The rest of the
// row -- that a card exists at all, and how many were in the deck -- is
// reconstructed from wherever the player's copies currently are, so a card
// leaving to somewhere this does not look at costs a greyed row and never a
// wrong count.

import { CardDescriptor } from './descriptor.js';
import { Game } from './game.js';
import { HoverCard } from './hover.js';
import { Setting } from './settings.js';
import { withCardImageRevision } from '../card_image_url.js';

/** The card types a constructed player deck is made of. */
const DECK_CARD_TYPES: ReadonlySet<string> = new Set([
    'Ally', 'Event', 'Upgrade', 'Support', 'Resource', 'PlayerSideScheme',
]);

type TrackedCard = {
    cardId: string;
    name: string;
    cost: number;
    remaining: number;
    total: number;
};

export class DeckTracker {
    private static panel = document.getElementById('deck-tracker') as HTMLElement | null;
    private static list = document.getElementById('deck-tracker-list') as HTMLElement | null;
    private static summary = document.getElementById('deck-tracker-summary') as HTMLElement | null;

    static toggle(): void {
        DeckTracker.panel?.classList.toggle('hide');
        DeckTracker.render();
    }

    static isOpen(): boolean {
        return DeckTracker.panel !== null && !DeckTracker.panel.classList.contains('hide');
    }

    /** Redraw if the panel is open. Called whenever the world changes. */
    static refresh(): void {
        if (DeckTracker.isOpen()) {
            DeckTracker.render();
        }
    }

    /**
     * Everywhere a card that started in the deck can currently be.
     *
     * Obligations and the identity are left out on purpose: an obligation
     * starts shuffled into the encounter deck and the identity is never in the
     * player deck, so neither belongs in a list of what you might still draw.
     */
    private static ownedAreas(): CardDescriptor[][] {
        const player = Game.world_descriptor?.players?.[Setting.player_id];
        if (!player) {
            return [];
        }
        return [
            player.hand_cards,
            player.player_discard_pile,
            player.allies,
            player.supports,
            player.set_aside_deck,
            player.additional_deck,
            player.additional_discard_pile,
            ...Object.values(player.special_decks ?? {}),
        ].filter(Boolean);
    }

    private static collect(): TrackedCard[] {
        const player = Game.world_descriptor?.players?.[Setting.player_id];
        if (!player) {
            return [];
        }

        const cards = new Map<string, TrackedCard>();
        const add = (card: CardDescriptor, inDeck: boolean): void => {
            const cardId = String(card.card_id ?? '');
            if (!cardId || !DECK_CARD_TYPES.has(String(card.card_type))) {
                return;
            }
            const entry = cards.get(cardId) ?? {
                cardId,
                name: String(card.name ?? cardId).replace(/^\*\s*/, ''),
                cost: Number(card.cost ?? 0),
                remaining: 0,
                total: 0,
            };
            entry.total += 1;
            if (inDeck) {
                entry.remaining += 1;
            }
            cards.set(cardId, entry);
        };

        for (const card of player.player_deck ?? []) {
            add(card, true);
        }
        for (const area of DeckTracker.ownedAreas()) {
            for (const card of area) {
                add(card, false);
            }
        }

        // By cost then name, which is how a decklist is written and, more to
        // the point, is not the order the cards will arrive in.
        return [...cards.values()].sort((left, right) =>
            left.cost - right.cost || left.name.localeCompare(right.name));
    }

    private static row(card: TrackedCard): HTMLElement {
        const row = document.createElement('li');
        row.className = card.remaining > 0 ? 'deck-tracker-row' : 'deck-tracker-row drawn';

        const cost = document.createElement('span');
        cost.className = 'deck-tracker-cost';
        cost.textContent = String(card.cost);

        const name = document.createElement('span');
        name.className = 'deck-tracker-name';
        name.textContent = card.name;

        const count = document.createElement('span');
        count.className = 'deck-tracker-count';
        // A single copy shows nothing, the way a decklist leaves the 1 off;
        // anything else shows how many are still in there.
        count.textContent = card.total > 1 ? String(card.remaining) : '';

        row.append(cost, name, count);
        row.title = card.remaining === card.total
            ? `${card.name} — all ${card.total} still in the deck`
            : `${card.name} — ${card.remaining} of ${card.total} left`;

        const preview = () => HoverCard.show(
            `url("${withCardImageRevision('/' + card.cardId)}")`,
            card.name, '', '', '', '', false);
        row.addEventListener('mouseenter', preview);
        row.addEventListener('mouseleave', () => HoverCard.hide());
        return row;
    }

    static render(): void {
        if (!DeckTracker.list || !DeckTracker.isOpen()) {
            return;
        }
        const cards = DeckTracker.collect();
        DeckTracker.list.replaceChildren(...cards.map(DeckTracker.row));

        const remaining = cards.reduce((sum, card) => sum + card.remaining, 0);
        const total = cards.reduce((sum, card) => sum + card.total, 0);
        if (DeckTracker.summary) {
            DeckTracker.summary.textContent = cards.length
                ? `${remaining} of ${total} cards left`
                : 'No deck to show yet.';
        }
    }
}
