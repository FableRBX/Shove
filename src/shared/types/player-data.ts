export const PLAYER_DATA_TOKEN = "PlayerData";

/**
 * The profile document as the client sees it through Replica. Defaults and
 * migrations are server-only: src/server/services/player/.
 */
export interface PlayerData {
	Version: number;
	Coins: number;
	Settings: { [key: string]: boolean };
}

/** Fields of PlayerData that are arrays, eligible for per-item inserts and removes. */
export type ArrayField = {
	[K in keyof PlayerData]: PlayerData[K] extends unknown[] ? K : never;
}[keyof PlayerData];

/** Fields of PlayerData that are maps (string-keyed tables), eligible for per-entry writes. */
export type MapField = {
	[K in keyof PlayerData]: PlayerData[K] extends unknown[]
		? never
		: PlayerData[K] extends { [id: string]: unknown }
			? K
			: never;
}[keyof PlayerData];
