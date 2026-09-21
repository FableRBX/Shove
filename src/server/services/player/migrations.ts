import type { PlayerData } from "shared/types/player-data";
import { deepCopy } from "server/util/deep-copy";

export const LATEST_VERSION = 1;

export type MigrationSteps = { [fromVersion: number]: (data: PlayerData) => void };

/**
 * Each entry upgrades a profile from its key's version to key + 1.
 * When changing the shape of PlayerData: bump LATEST_VERSION, add a step here.
 * Example step, upgrading version 1 profiles after a hypothetical settings change:
 *   [1]: (data) => { data.Settings.music = data.Settings.music ?? true; }
 */
const MIGRATIONS: MigrationSteps = {};

/**
 * Returns `data` itself when it is already at LATEST_VERSION or newer (no copy
 * cost on the common path). Otherwise returns a migrated deep copy; the source
 * is never mutated, so a throwing step cannot leave a half-migrated profile
 * behind for EndSession to save.
 */
export function migrate(data: PlayerData, steps: MigrationSteps = MIGRATIONS): PlayerData {
	if (data.Version >= LATEST_VERSION) return data;

	const staged = deepCopy(data);
	while (staged.Version < LATEST_VERSION) {
		const step = steps[staged.Version];
		if (step === undefined) {
			error(`[push-a-giant] missing migration from profile version ${staged.Version}`);
		}
		step(staged);
		staged.Version += 1;
	}
	return staged;
}
