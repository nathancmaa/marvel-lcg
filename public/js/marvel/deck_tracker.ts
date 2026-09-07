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
    private static advice = document.getElementById('deck-tracker-advice') as HTMLElement | null;
    private static list = document.getElementById('deck-tracker-list') as HTMLElement | null;
    private static summary = document.getElementById('deck-tracker-summary') as HTMLElement | null;

    static toggle(): void {
        DeckTracker.panel?.classList.toggle('hide');
        DeckTracker.render();
    }

    static close(): void {
        DeckTracker.panel?.classList.add('hide');
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

    /**
     * What to look for in the opening hand.
     *
     * Two different claims, and the panel never blurs them. When the deck's
     * author wrote about the mulligan -- roughly one deck in four -- these are
     * their cards and their words, and we only mark which are in hand. When
     * they did not, the cards are ranked from the deck's own composition, and
     * the heading says so: that ranking finds about a third of what an author
     * would have named, against a sixth by chance, which is worth showing and
     * not worth mistaking for the author's own advice.
     */
    private static renderAdvice(): void {
        const panel = DeckTracker.advice;
        if (!panel) {
            return;
        }
        const player = Game.world_descriptor?.players?.[Setting.player_id];
        panel.replaceChildren();
        panel.classList.add('hide');

        const inHand = new Set(
            (player?.hand_cards ?? []).map((card) => String(card.card_id ?? '')));
        const byId = new Map<string, string>();
        for (const area of [player?.player_deck ?? [], ...DeckTracker.ownedAreas()]) {
            for (const card of area) {
                const cardId = String(card.card_id ?? '');
                if (cardId && !byId.has(cardId)) {
                    byId.set(cardId, String(card.name ?? cardId).replace(/^\*\s*/, ''));
                }
            }
        }

        // Only cards this deck actually holds. An author can name a card they
        // later cut, and a reprint carries a different id from the one they
        // linked -- either way the card is not here to be drawn, and a chip
        // for it would show a bare number that could never light up.
        const wanted = (player?.mulligan_cards ?? []).filter(
            (cardId) => byId.has(cardId));
        if (!wanted.length) {
            return;
        }
        panel.classList.remove('hide');

        const fromAuthor = player?.mulligan_source === 'author';
        const heading = document.createElement('div');
        heading.className = fromAuthor
            ? 'deck-tracker-advice-head'
            : 'deck-tracker-advice-head guessed';
        heading.textContent = fromAuthor ? 'Author looks for' : 'Worth digging for';
        heading.title = fromAuthor
            ? "The cards this deck's author named when writing about the mulligan."
            : 'Nobody wrote mulligan advice for this deck, so these are ranked '
              + 'from what it is made of: permanents, your own kit, and cards '
              + 'you run three of. Cost is ignored -- it does not predict.';
        panel.appendChild(heading);

        const chips = document.createElement('div');
        chips.className = 'deck-tracker-chips';
        for (const cardId of wanted) {
            const chip = document.createElement('span');
            const held = inHand.has(cardId);
            chip.className = held ? 'deck-tracker-chip held' : 'deck-tracker-chip';
            chip.textContent = byId.get(cardId) as string;
            chip.title = held ? 'In your hand' : 'Not in hand';
            chips.appendChild(chip);
        }
        panel.appendChild(chips);

        const note = fromAuthor ? String(player?.mulligan_note ?? '') : '';
        if (note) {
            const quote = document.createElement('p');
            quote.className = 'deck-tracker-quote';
            quote.textContent = note;
            panel.appendChild(quote);
        } else if (!fromAuthor) {
            const basis = document.createElement('p');
            basis.className = 'deck-tracker-quote';
            basis.textContent = "Ranked from this deck, not the author's notes.";
            panel.appendChild(basis);
        }
    }

    /**
     * Wire the close once, at import.
     *
     * A static initialiser block would be the obvious home, but the build
     * targets es2021 and those are es2022. The class is imported for its side
     * effect either way.
     */
    static bindClose(): void {
        const close = document.getElementById('deck-tracker-close');
        close?.addEventListener('click', () => DeckTracker.close());
        close?.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                DeckTracker.close();
            }
        });
    }

    static render(): void {
        if (!DeckTracker.list || !DeckTracker.isOpen()) {
            return;
        }
        DeckTracker.renderAdvice();
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

DeckTracker.bindClose();
