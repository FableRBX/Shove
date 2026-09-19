import { describe, expect, it } from "@rbxts/jest-globals";
import { deepCopy } from "./deep-copy";

describe("deepCopy", () => {
	it("returns primitives unchanged", () => {
		expect(deepCopy(5)).toBe(5);
		expect(deepCopy("x")).toBe("x");
		expect(deepCopy(true)).toBe(true);
	});

	it("copies nested tables so mutating the copy leaves the source untouched", () => {
		const source = { Version: 1, Settings: { music: true } };
		const copy = deepCopy(source);
		copy.Settings.music = false;
		copy.Version = 2;
		expect(source.Settings.music).toBe(true);
		expect(source.Version).toBe(1);
		expect(copy.Settings).never.toBe(source.Settings);
	});

	it("preserves arrays", () => {
		const source = { Items: ["a", "b"] };
		const copy = deepCopy(source);
		expect(copy.Items).toEqual(["a", "b"]);
		expect(copy.Items).never.toBe(source.Items);
	});
});
