import { Notify } from "./notify.js";

export class Command {

    static async saveLocal(): Promise<string> {
        const response = await fetch("save_local", { method: "POST" });
        const data = await response.json();
        if( !response.ok ) {
            const error = data.error || `Replay save failed: ${response.status}`
            Notify.showCommand(error)
            throw new Error(error)
        }

        const path = data.path || data.file
        Notify.showCommand(`Replay saved: ${path}`)
        return path
    }

    static async saveGameRatings(ratings: {
        hero_rating?: number|null,
        scenario_rating?: number|null,
    }): Promise<{hero_rating: number|null, scenario_rating: number|null}> {
        const response = await fetch('/game_ratings/save', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(ratings),
        })
        const data = await response.json()
        if( !response.ok ) {
            throw new Error(data.error || `Rating save failed: ${response.status}`)
        }
        return data
    }

}
