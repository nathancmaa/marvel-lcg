// The pane that shows the standing answers and the order they fire in.
//
// Reachable from the button panel, beside Log and Deck, because the order is
// something you set once and then check when a game does something you did not
// expect. The card's own check-circle is still how a card gets on the list;
// this is where the list is read and rearranged.

import { HoverCard } from './hover.js'
import { StandingAnswers } from './standing_answers.js'
import { withCardImageRevision } from '../card_image_url.js'

export class StandingPanel {
    private static panel = document.getElementById('standing-answers') as HTMLElement | null;
    private static list = document.getElementById('standing-answers-list') as HTMLElement | null;
    private static empty = document.getElementById('standing-answers-empty') as HTMLElement | null;

    static toggle(): void {
        StandingPanel.panel?.classList.toggle('hide');
        StandingPanel.render();
    }

    static close(): void {
        StandingPanel.panel?.classList.add('hide');
    }

    static isOpen(): boolean {
        return StandingPanel.panel !== null
            && !StandingPanel.panel.classList.contains('hide');
    }

    private static row(card_id: string, name: string, at: number, of: number): HTMLElement {
        const row = document.createElement('li');
        row.className = 'standing-row';

        const rank = document.createElement('span');
        rank.className = 'standing-rank';
        rank.textContent = String(at + 1);

        const label = document.createElement('span');
        label.className = 'standing-name';
        label.textContent = name;
        // The same preview the deck tracker gives, since the name alone is not
        // always enough to remember which trigger this is.
        label.addEventListener('mouseenter', () => {
            HoverCard.show(`url("${withCardImageRevision('/' + card_id)}")`,
                name, '', '', '', '', false);
        });
        label.addEventListener('mouseleave', () => HoverCard.hide());

        const controls = document.createElement('span');
        controls.className = 'standing-controls';

        const up = document.createElement('button');
        up.type = 'button';
        up.className = 'standing-move';
        up.textContent = '↑';
        up.title = `Resolve ${name} earlier`;
        up.disabled = at === 0;
        up.addEventListener('click', () => StandingAnswers.move(card_id, -1));

        const down = document.createElement('button');
        down.type = 'button';
        down.className = 'standing-move';
        down.textContent = '↓';
        down.title = `Resolve ${name} later`;
        down.disabled = at === of - 1;
        down.addEventListener('click', () => StandingAnswers.move(card_id, 1));

        const remove = document.createElement('button');
        remove.type = 'button';
        remove.className = 'standing-remove';
        remove.textContent = '×';
        remove.title = `Ask about ${name} again`;
        remove.addEventListener('click', () => StandingAnswers.remove(card_id));

        controls.append(up, down, remove);
        row.append(rank, label, controls);
        return row;
    }

    static render(): void {
        if( !StandingPanel.list || !StandingPanel.empty ) {
            return;
        }
        const answers = StandingAnswers.list();
        StandingPanel.empty.classList.toggle('hide', answers.length > 0);
        StandingPanel.list.replaceChildren(...answers.map(
            (entry, at) => StandingPanel.row(
                entry.card_id, entry.name, at, answers.length)));
    }

    /**
     * Wired here rather than in a static block, so the panel redraws whenever
     * the list changes -- including from the card's own check-circle, which is
     * the usual way something arrives on it.
     */
    static bind(): void {
        const close = document.getElementById('standing-answers-close');
        close?.addEventListener('click', () => StandingPanel.close());
        close?.addEventListener('keydown', (event) => {
            if( (event as KeyboardEvent).key === 'Enter' ) {
                StandingPanel.close();
            }
        });
        StandingAnswers.onChanged(() => StandingPanel.render());
        StandingPanel.render();
    }
}

StandingPanel.bind();
