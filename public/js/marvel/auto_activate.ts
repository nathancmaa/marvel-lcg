import { Cards } from './cards.js'
import { ClassName } from './class_name.js'
import { Effect } from './effect.js';
import { ButtonSetting, Setting } from './settings.js';
import { StandingAnswers } from './standing_answers.js';

export class AutoActivate
{
    /**
     * The marked cards, in the order they should fire.
     *
     * Kept as a view onto StandingAnswers rather than a set of its own: the
     * order is the whole point once two marked cards trigger together, and a
     * Set cannot hold one.
     */
    static get config(): {has(card_id: string): boolean} {
        return StandingAnswers
    }

    static applyConfig() {
        document.querySelectorAll<HTMLElement>('.card').forEach(card_div =>
        {
            const object_id = Number(card_div.dataset.id!)
            const card_id = Cards.getCard(object_id)!.card_id
            if( AutoActivate.config.has(card_id) ) {
                card_div.classList.add(ClassName.auto_activate)
            }
            else if( card_div.classList.contains(ClassName.auto_activate) ) {
                card_div.classList.remove(ClassName.auto_activate)
            }
        })
    }

    /**
     * Keep the ticks on the board agreeing with the list.
     *
     * The list can change from the pane as well as from a card, and a card
     * removed there was still showing its tick -- two places claiming
     * different things about the same card.
     */
    static {
        StandingAnswers.onChanged(() => AutoActivate.applyConfig())
    }

    static isHasAutoActivate() {
        if( ButtonSetting.is_replay ) {
            return false
        }
        for( const option of Effect.response_json_ask.options ) {
            let name = option.name_with_space;
            if (["Flip to alter-ego form", "Ask", "Change form", "Change Form", 'Defense'].includes(name)) {
                return false;
            }
            const card_id = Cards.getCard(option.bind_id)?.card_id
            if( card_id && StandingAnswers.has(card_id) ) {
                return true
            }
        }
        return false
    }

    static checkCanAutoActivate(object_id: number) {
        if( !ButtonSetting.auto_activate ) {
            return false
        }
        if( ButtonSetting.is_replay ) {
            return false
        }
        // if( Setting.is_hot_seat ) {
        //     return true
        // }
        const card = Cards.getCard(object_id)
        if( Setting.player_id == card?.control_player ) {
            return true
        } else {
            return false
        }
    }

    static isAutoActivate(object_id: number) {
        if( !AutoActivate.checkCanAutoActivate(object_id) ) {
            return false
        }
        const card = Cards.getCard(object_id)
        if( !card ) {
            return false
        }
        return StandingAnswers.has(card.card_id)
    }

    static isAutoActivate2(card_div: HTMLElement) {
        const object_id = Number(card_div.dataset.id!)
        if( !AutoActivate.checkCanAutoActivate(object_id) ) {
            return false
        }
        return card_div.classList.contains(ClassName.auto_activate)
    }
}

(window as any).AutoActivate = AutoActivate;

