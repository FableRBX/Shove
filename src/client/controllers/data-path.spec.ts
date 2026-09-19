import { describe, expect, it } from "@rbxts/jest-globals";
import { getAt, snapshot } from "./data-path";

const data = {
	Coins: 3,
	Settings: { music: { Enabled: true, Volume: 5 } },
	Inventory: ["@1", "@2"],
};

describe("getAt", () => {
	it("reads a nested value", () => {
		expect(getAt(data, ["Settings", "music", "Volume"])).toBe(5);
		expect(getAt(data, ["Coins"])).toBe(3);
	});

	it("returns the document for the empty path", () => {
		expect(getAt(data, [])).toBe(data);
	});

	it("is undefined when a step is missing", () => {
		expect(getAt(data, ["Settings", "sfx", "Volume"])).toBeUndefined();
		expect(getAt(data, ["Nope"])).toBeUndefined();
	});

	it("is undefined when a step is not a table", () => {
		expect(getAt(data, ["Coins", "x"])).toBeUndefined();
		expect(getAt(undefined, ["Coins"])).toBeUndefined();
	});

	it("uses a numeric key as Replica ships it: a Luau one-based index", () => {
		expect(getAt(data, ["Inventory", 1])).toBe("@1");
		expect(getAt(data, ["Inventory", 3])).toBeUndefined();
	});
});

describe("snapshot", () => {
	it("returns primitives and undefined as they are", () => {
		expect(snapshot(5)).toBe(5);
		expect(snapshot("x")).toBe("x");
		expect(snapshot(undefined)).toBeUndefined();
	});

	it("clones a table one level deep", () => {
		const copy = snapshot(data.Settings);
		expect(copy).never.toBe(data.Settings);
		expect(copy).toEqual(data.Settings);
		expect(copy.music).toBe(data.Settings.music);
	});
});
