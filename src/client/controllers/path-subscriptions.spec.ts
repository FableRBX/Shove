import { describe, expect, it } from "@rbxts/jest-globals";
import { PathSubscriptions, pathsOverlap } from "./path-subscriptions";
import type { DataChange, DataPath } from "./player-data-store";

const change = (path: DataPath): DataChange => ({ action: "Set", path, value: 1, detail: 0 });

describe("pathsOverlap", () => {
	it("is true for equal paths", () => {
		expect(pathsOverlap(["Coins"], ["Coins"])).toBe(true);
		expect(pathsOverlap(["Settings", "music"], ["Settings", "music"])).toBe(true);
	});

	it("is true when either path is a prefix of the other", () => {
		expect(pathsOverlap(["Settings"], ["Settings", "music"])).toBe(true);
		expect(pathsOverlap(["Settings", "music"], ["Settings"])).toBe(true);
	});

	it("is false for siblings", () => {
		expect(pathsOverlap(["Coins"], ["Settings"])).toBe(false);
		expect(pathsOverlap(["Settings", "music"], ["Settings", "sfx"])).toBe(false);
	});

	it("treats the empty path as a prefix of everything", () => {
		expect(pathsOverlap([], ["Coins"])).toBe(true);
		expect(pathsOverlap(["Coins", "x"], [])).toBe(true);
		expect(pathsOverlap([], [])).toBe(true);
	});
});

describe("PathSubscriptions", () => {
	it("fires root subscribers first, then the change's bucket, each in subscription order", () => {
		const subscriptions = new PathSubscriptions();
		const order: string[] = [];
		subscriptions.subscribe(["Coins"], () => {
			order.push("coins-1");
		});
		subscriptions.subscribe([], () => {
			order.push("root-1");
		});
		subscriptions.subscribe(["Coins"], () => {
			order.push("coins-2");
		});
		subscriptions.subscribe([], () => {
			order.push("root-2");
		});

		subscriptions.dispatch(change(["Coins"]));

		expect(order).toEqual(["root-1", "root-2", "coins-1", "coins-2"]);
	});

	it("hands the listener the change itself", () => {
		const subscriptions = new PathSubscriptions();
		const received: DataChange[] = [];
		subscriptions.subscribe(["Inventory"], (c) => {
			received.push(c);
		});
		const sent: DataChange = { action: "TableInsert", path: ["Inventory"], value: "@1", detail: 1 };

		subscriptions.dispatch(sent);

		expect(received.size()).toBe(1);
		expect(received[0]).toBe(sent);
	});

	it("leaves an unrelated bucket untouched", () => {
		const subscriptions = new PathSubscriptions();
		let fired = 0;
		subscriptions.subscribe(["Settings"], () => {
			fired += 1;
		});

		subscriptions.dispatch(change(["Coins"]));

		expect(fired).toBe(0);
	});

	it("filters within a bucket: an entry write reaches the field and that entry only", () => {
		const subscriptions = new PathSubscriptions();
		const fired: string[] = [];
		subscriptions.subscribe(["Settings"], () => {
			fired.push("field");
		});
		subscriptions.subscribe(["Settings", "music"], () => {
			fired.push("music");
		});
		subscriptions.subscribe(["Settings", "sfx"], () => {
			fired.push("sfx");
		});

		subscriptions.dispatch(change(["Settings", "music"]));

		expect(fired).toEqual(["field", "music"]);
	});

	it("reaches every entry beneath a wholesale field write", () => {
		const subscriptions = new PathSubscriptions();
		const fired: string[] = [];
		subscriptions.subscribe(["Settings", "music"], () => {
			fired.push("music");
		});
		subscriptions.subscribe(["Settings", "sfx"], () => {
			fired.push("sfx");
		});

		subscriptions.dispatch(change(["Settings"]));

		expect(fired).toEqual(["music", "sfx"]);
	});

	it("reaches every bucket for an empty-path change", () => {
		const subscriptions = new PathSubscriptions();
		const fired: string[] = [];
		subscriptions.subscribe(["Coins"], () => {
			fired.push("Coins");
		});
		subscriptions.subscribe(["Settings"], () => {
			fired.push("Settings");
		});

		subscriptions.dispatch(change([]));

		// Bucket order is unspecified for a root change; only membership is.
		expect(fired.sort()).toEqual(["Coins", "Settings"]);
	});

	it("stops firing after unsubscribe and drops the count", () => {
		const subscriptions = new PathSubscriptions();
		let fired = 0;
		const unsubscribe = subscriptions.subscribe(["Coins"], () => {
			fired += 1;
		});
		expect(subscriptions.count()).toBe(1);

		unsubscribe();
		unsubscribe();
		subscriptions.dispatch(change(["Coins"]));

		expect(fired).toBe(0);
		expect(subscriptions.count()).toBe(0);
	});

	it("reports a throwing listener and still runs the next", () => {
		const subscriptions = new PathSubscriptions();
		let fired = false;
		subscriptions.subscribe(["Coins"], () => {
			throw "boom";
		});
		subscriptions.subscribe(["Coins"], () => {
			fired = true;
		});

		expect(() => subscriptions.dispatch(change(["Coins"]))).never.toThrow();
		expect(fired).toBe(true);
	});
});
