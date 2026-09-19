import { describe, expect, it } from "@rbxts/jest-globals";
import { shouldCancelProfileLoad, shouldKickOnSessionEnd } from "./session-policy";

describe("shouldKickOnSessionEnd", () => {
	it("kicks when another server stole the session", () => {
		expect(shouldKickOnSessionEnd({ intentional: false, serverClosing: false, playerPresent: true })).toBe(true);
	});

	it("does not kick when this server ended the session itself", () => {
		expect(shouldKickOnSessionEnd({ intentional: true, serverClosing: false, playerPresent: true })).toBe(false);
	});

	it("does not kick during server shutdown", () => {
		expect(shouldKickOnSessionEnd({ intentional: false, serverClosing: true, playerPresent: true })).toBe(false);
	});

	it("does not kick a player who already left", () => {
		expect(shouldKickOnSessionEnd({ intentional: false, serverClosing: false, playerPresent: false })).toBe(false);
	});
});

describe("shouldCancelProfileLoad", () => {
	it("keeps waiting while the player is present and under the timeout", () => {
		expect(shouldCancelProfileLoad(true, 10, 120)).toBe(false);
	});

	it("cancels when the player has left", () => {
		expect(shouldCancelProfileLoad(false, 10, 120)).toBe(true);
	});

	it("cancels once the timeout is reached", () => {
		expect(shouldCancelProfileLoad(true, 120, 120)).toBe(true);
	});
});
