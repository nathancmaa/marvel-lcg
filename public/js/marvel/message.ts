import { Command } from "./command.js";
import { Game } from "./game.js";
import { recordCampaignVictory } from "../campaign_state.js";
import { UserSettings } from "../user_settings.js";
import { Setting } from "./settings.js";
import { canPushToBgStats, sendToBgStats, type BgStatsGame } from "../bgstats_play.js";

export class Message {

    private static overlay: HTMLElement
    private static messageElement: HTMLElement

    private static game_over_div: HTMLElement
    private static end_messageElement: HTMLElement
    private static end_messageElementText: HTMLElement
    private static retryButton: HTMLButtonElement
    private static saveReplayButton: HTMLButtonElement
    private static bgStatsButton: HTMLButtonElement
    private static replaySavePromise: Promise<string>|null = null
    private static autoSaveAttempted = false
    private static ratingPanel: HTMLElement
    private static ratingStatus: HTMLElement
    private static ratings: {hero: number|null, scenario: number|null} = {
        hero: null,
        scenario: null,
    }
    private static ratingSavePromise: Promise<void> = Promise.resolve()

    private static renderRating(kind: 'hero'|'scenario') {
        const stars = Message.ratingPanel.querySelectorAll<HTMLButtonElement>(
            `[data-rating-kind="${kind}"] button`
        )
        stars.forEach((button) => {
            const selected = Number(button.dataset.value) <= (Message.ratings[kind] || 0)
            button.classList.toggle('selected', selected)
            button.textContent = selected ? '★' : '☆'
            button.setAttribute('aria-pressed', String(selected))
        })
    }

    private static selectRating(kind: 'hero'|'scenario', value: number) {
        const previous = Message.ratings[kind]
        Message.ratings[kind] = value
        Message.renderRating(kind)
        Message.ratingStatus.textContent = 'Saving…'

        Message.ratingSavePromise = Message.ratingSavePromise
            .catch(() => {})
            .then(async () => {
                try {
                    await Command.saveGameRatings({[`${kind}_rating`]: value})
                    Message.ratingStatus.textContent = 'Saved · ratings can be changed anytime on this screen'
                } catch( error ) {
                    if( Message.ratings[kind] === value ) {
                        Message.ratings[kind] = previous
                        Message.renderRating(kind)
                    }
                    Message.ratingStatus.textContent = 'Could not save the rating'
                    console.error(error)
                }
            })
    }

    private static initRatings() {
        Message.ratingPanel = document.getElementById('game-over-ratings')!
        Message.ratingStatus = document.getElementById('game-over-rating-status')!
        const groups = Message.ratingPanel.querySelectorAll<HTMLElement>('.game-over-rating-stars')
        groups.forEach((group) => {
            const kind = group.dataset.ratingKind as 'hero'|'scenario'
            for( let value = 1; value <= 5; value++ ) {
                const button = document.createElement('button')
                button.type = 'button'
                button.dataset.value = String(value)
                button.textContent = '☆'
                button.setAttribute('aria-label', `Rate ${kind} ${value} out of 5`)
                button.setAttribute('aria-pressed', 'false')
                button.addEventListener('click', () => Message.selectRating(kind, value))
                group.appendChild(button)
            }
        })
    }

    private static async saveReplay(automatic: boolean) {
        if( Message.replaySavePromise ) {
            return Message.replaySavePromise
        }

        Message.saveReplayButton.disabled = true
        Message.saveReplayButton.innerHTML = '<i class="fa fa-spinner fa-spin" aria-hidden="true"></i> Saving...'
        Message.replaySavePromise = Command.saveLocal()

        try {
            const path = await Message.replaySavePromise
            const label = automatic ? 'Autosaved' : 'Saved'
            Message.saveReplayButton.innerHTML = `<i class="fa fa-check" aria-hidden="true"></i> ${label}`
            return path
        } catch( error ) {
            console.error(error)
            Message.saveReplayButton.disabled = false
            Message.saveReplayButton.innerHTML = '<i class="fa fa-download" aria-hidden="true"></i> Save replay'
            throw error
        } finally {
            Message.replaySavePromise = null
        }
    }

    private static autoSaveReplay() {
        if( Message.autoSaveAttempted || Setting.replay_mode || !UserSettings.getAutoSaveReplays() ) {
            return
        }

        Message.autoSaveAttempted = true
        void Message.saveReplay(true).catch(() => {
            // Manual saving remains available after an autosave error.
        })
    }

    static init() {
        Message.overlay = document.getElementById('message-overlay')!;
        Message.messageElement = document.getElementById('message-text')!;

        Message.game_over_div = document.getElementById('game-over-box')!;
        // Message.end_overlay = document.getElementById('message-overlay')!;
        Message.end_messageElement = document.getElementById('game-over-text')!;
        Message.end_messageElementText = document.getElementById('game-over-text-2')!;
        const game_over_buttons = document.getElementById('game-over-buttons')!;
        Message.initRatings()

        Message.saveReplayButton = document.createElement('button');
        Message.saveReplayButton.innerHTML = '<i class="fa fa-download" aria-hidden="true"></i> Save replay';
        Message.saveReplayButton.classList.add('save-replay')
        Message.saveReplayButton.addEventListener('click', async function() {
            try {
                await Message.saveReplay(false)
            } catch( _ ) {
                // saveReplay already reports the error and restores the button.
            }
        });

        Message.retryButton = document.createElement('button');
        Message.retryButton.innerHTML = '<i class="fa fa-repeat" aria-hidden="true"></i> Try again';
        Message.retryButton.classList.add('try-again');
        Message.retryButton.hidden = true;
        Message.retryButton.addEventListener('click', async function() {
            Message.retryButton.disabled = true;
            Message.retryButton.innerHTML = '<i class="fa fa-spinner fa-spin" aria-hidden="true"></i> Starting...';

            try {
                const response = await fetch('retry', { method: 'POST' });
                if( !response.ok ) {
                    throw new Error(`Retry failed: ${response.status}`);
                }
                Game.setGameOver(false);
            } catch( error ) {
                console.error(error);
                Message.retryButton.disabled = false;
                Message.retryButton.innerHTML = '<i class="fa fa-repeat" aria-hidden="true"></i> Try again';
            }
        });

        // The same handoff as the history page's button, for the game just
        // finished, without going to the history page to find it.
        Message.bgStatsButton = document.createElement('button');
        Message.bgStatsButton.classList.add('bg-stats');
        Message.bgStatsButton.hidden = true;
        Message.bgStatsButton.addEventListener('click', () => void Message.sendToBgStats());

        const buttonMainMenu = document.createElement('button');
        buttonMainMenu.innerHTML = '<i class="fa fa-home" aria-hidden="true"></i> Main menu';
        buttonMainMenu.classList.add('main-menu');
        buttonMainMenu.addEventListener('click', function() {
            window.location.assign('/');
        });

        game_over_buttons.appendChild(Message.retryButton);
        game_over_buttons.appendChild(buttonMainMenu);
        game_over_buttons.appendChild(Message.saveReplayButton);
        game_over_buttons.appendChild(Message.bgStatsButton);
    }

    private static resetBgStatsButton() {
        Message.bgStatsButton.disabled = false;
        Message.bgStatsButton.innerHTML = '<i class="fa fa-bar-chart" aria-hidden="true"></i> BG Stats';
    }

    /**
     * Hand the finished game to BG Stats.
     *
     * The game is read back from the history rather than from the table, so
     * what goes to BG Stats is exactly what the history page would send for
     * the same row -- and asking the history is what records the game if
     * the end of it has not yet.
     */
    private static async sendToBgStats() {
        Message.bgStatsButton.disabled = true;
        Message.bgStatsButton.innerHTML = '<i class="fa fa-spinner fa-spin" aria-hidden="true"></i> BG Stats';
        try {
            const response = await fetch('/game_history/current');
            const data = await response.json();
            if( !response.ok ) {
                throw new Error(data.error || `${response.status} ${response.statusText}`);
            }
            const game = data as BgStatsGame;
            if( !canPushToBgStats(game) ) {
                throw new Error('This game has no result to send.');
            }
            sendToBgStats(game, UserSettings.getBgStatsPlayerName() || 'Me', UserSettings.getBgStatsLocation());
            Message.bgStatsButton.innerHTML = '<i class="fa fa-check" aria-hidden="true"></i> Sent to BG Stats';
            Message.bgStatsButton.disabled = false;
        } catch( error ) {
            console.error(error);
            Message.bgStatsButton.innerHTML = '<i class="fa fa-exclamation-triangle" aria-hidden="true"></i> BG Stats';
            Message.bgStatsButton.title = error instanceof Error ? error.message : String(error);
            Message.bgStatsButton.disabled = false;
        }
    }

    static cleanGameOverMessage() {
        Message.game_over_div.classList.remove('active');
        Message.autoSaveAttempted = false
        Message.replaySavePromise = null
        Message.ratings = {hero: null, scenario: null}
        Message.renderRating('hero')
        Message.renderRating('scenario')
        Message.ratingStatus.textContent = 'Optional · 1–5 stars'
        Message.ratingPanel.hidden = true
    }

    static showGameOverMessage(text: string) {
        Message.game_over_div.classList.add('active');
        Message.overlay.classList.remove('active');
        if( Game.players_won ) {
            Message.end_messageElement.textContent = "VICTORY";
            void recordCampaignVictory().catch((error) => {
                console.error('Could not update campaign progress', error)
            })
        } else {
            Message.end_messageElement.textContent = "DEFEAT";
        }
        Message.retryButton.hidden = Game.players_won;
        Message.retryButton.disabled = false;
        Message.retryButton.innerHTML = '<i class="fa fa-repeat" aria-hidden="true"></i> Try again';
        if( !Message.autoSaveAttempted && !Message.replaySavePromise ) {
            Message.saveReplayButton.disabled = false;
            Message.saveReplayButton.innerHTML = '<i class="fa fa-download" aria-hidden="true"></i> Save replay';
        }
        Message.end_messageElementText.textContent = text
        Message.ratingPanel.hidden = Setting.replay_mode
        // A replay is not a play; the rest is decided by the history when
        // the button is pressed, which is where "this game does not count"
        // is known.
        Message.bgStatsButton.hidden = Setting.replay_mode
        Message.bgStatsButton.title = 'Send this game to BG Stats'
        Message.resetBgStatsButton()
        Message.autoSaveReplay()
    }

    static showMessage(text: string, original_duration: number|null = 1200) {
        // Show the overlay
        Message.overlay.classList.add('active');

        let duration = 1200
        if( original_duration != null ) {
            duration = original_duration
        }

        let sec = duration / 1000
        if( Game.game_over ) {
            Message.showGameOverMessage(text)
        } else
        if( original_duration == null ) {
            Message.messageElement.textContent = text;
            Message.overlay.style.animation = `overlay-move-once ${sec}s forwards`
        } else {
            Message.messageElement.textContent = text;
            Message.overlay.style.animation = `overlay-move ${sec}s forwards`
        }

        // Hide the overlay after the specified duration
        if( !Game.game_over && original_duration != null ) {
            setTimeout(() => {
                Message.overlay.style.animation = ""
                Message.overlay.classList.remove('active');
                // if( !Game.game_over ) {
                //     Message.game_over_div.classList.remove('active');
                // }
            }, duration);
        }
    }
}
