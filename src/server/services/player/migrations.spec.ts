import { describe, expect, it } from "@rbxts/jest-globals";
import { DEFAULT_PLAYER_DATA } from "./player-data-defaults";
import { LATEST_VERSION, migrate } from "./migrations";
import type { PlayerData } from "shared/types/player-data";

// Steps here touch only spine-owned fields (Version, Settings), so deleting a
// feature's schema field never reaches this spec.
function behindByOne(): PlayerData {
	return { ...DEFAULT_PLAYER_DATA, Version: LATEST_VERSION - 1, Settings: { legacy: true } };
}

describe("migrate", () => {
	it("returns a current-version profile as-is, without copying", () => {
		const data = { ...DEFAULT_PLAYER_DATA, Settings: { ...DEFAULT_PLAYER_DATA.Settings } };
		expect(migrate(data)).toBe(data);
	});

	it("returns a future-version profile as-is", () => {
		const data = { ...DEFAULT_PLAYER_DATA, Version: LATEST_VERSION + 1 };
		expect(migrate(data)).toBe(data);
	});

	it("returns a migrated copy of a profile that is behind", () => {
		const data = behindByOne();
		const result = migrate(data, { [LATEST_VERSION - 1]: (d) => (d.Settings.migrated = true) });
		expect(result.Version).toBe(LATEST_VERSION);
		expect(result.Settings.migrated).toBe(true);
		expect(data.Version).toBe(LATEST_VERSION - 1);
		expect(data.Settings.migrated).toBeUndefined();
	});

	it("leaves the source untouched when a step throws", () => {
		const data = behindByOne();
		const explode = (d: PlayerData) => {
			d.Settings.poisoned = true;
			error("boom");
		};
		expect(() => migrate(data, { [LATEST_VERSION - 1]: explode })).toThrow();
		expect(data.Settings.poisoned).toBeUndefined();
		expect(data.Version).toBe(LATEST_VERSION - 1);
	});

	it("throws when a migration step is missing", () => {
		const data = { ...DEFAULT_PLAYER_DATA, Version: LATEST_VERSION - 1 };
		expect(() => migrate(data, {})).toThrow();
	});
});
