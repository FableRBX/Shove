import type { DataPath } from "./player-data-store";

/**
 * Reads the value at `path`, or undefined when any step is missing or not a
 * table. Keys are used as Replica ships them: a numeric key is a Luau
 * one-based index, so `["Inventory", 1]` is the first item.
 */
export function getAt(data: unknown, path: DataPath): unknown {
	let current = data;
	for (const key of path) {
		if (!typeIs(current, "table")) return undefined;
		// A record, not an array, so roblox-ts does not shift the numeric key.
		current = (current as Record<string | number, unknown>)[key];
	}
	return current;
}

/**
 * A shallow clone for a table, the value itself otherwise: what a hook hands
 * to React, so a mirror that Replica mutates in place still reads as changed.
 */
export function snapshot<T>(value: T): T {
	return typeIs(value, "table") ? (table.clone(value) as T) : value;
}
