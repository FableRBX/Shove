import { describe, expect, it } from "@rbxts/jest-globals";

describe("test harness", () => {
	it("runs specs in-engine", () => {
		expect(1 + 1).toBe(2);
	});
});
