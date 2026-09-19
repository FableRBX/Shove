import type { PlayerData } from "shared/types/player-data";
import { LATEST_VERSION } from "./migrations";

/** ProfileStore template: new profiles start here and Reconcile fills old ones. */
export const DEFAULT_PLAYER_DATA: PlayerData = {
	Version: LATEST_VERSION,
	Coins: 0,
	Settings: {},
};
