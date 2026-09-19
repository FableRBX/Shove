import { describe, expect, it } from "@rbxts/jest-globals";
import { canRequestCoin } from "./can-request-coin";

describe("canRequestCoin", () => {
	it("allows the first request", () => {
		expect(canRequestCoin(undefined, 100, 1)).toBe(true);
	});

	it("blocks a request inside the cooldown", () => {
		expect(canRequestCoin(100, 100.5, 1)).toBe(false);
	});

	it("allows a request after the cooldown", () => {
		expect(canRequestCoin(100, 101, 1)).toBe(true);
	});
});
