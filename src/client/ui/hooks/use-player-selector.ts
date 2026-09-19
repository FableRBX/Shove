import { useLatest } from "@rbxts/pretty-react-hooks";
import { useEffect, useState } from "@rbxts/react";
import type { PlayerData } from "shared/types/player-data";
import { usePlayerDataStore } from "../player-data-context";

const strictEquals = <T>(a: T, b: T) => a === b;

/**
 * Recomputes on changes to `fields` only; re-renders when `equals` (default
 * ===) says the result changed. Return a primitive or build a new value,
 * never a sub-table of the mirror: Replica mutates those in place, so an
 * unchanged reference would never re-render.
 */
export function usePlayerSelector<T>(
	fields: ReadonlyArray<keyof PlayerData>,
	selector: (data: Readonly<PlayerData>) => T,
	equals: (a: T, b: T) => boolean = strictEquals,
): T | undefined {
	const store = usePlayerDataStore();
	// Latest closures without re-subscribing: an inline selector or equals is a
	// new function every render.
	const selectorRef = useLatest(selector);
	const equalsRef = useLatest(equals);
	const [value, setValue] = useState<T | undefined>(() => {
		const data = store.getData();
		return data === undefined ? undefined : selector(data);
	});

	// An inline field list is a new array every render; key the effect on its contents.
	const fieldsKey = fields.join(",");
	useEffect(() => {
		const update = () => {
			const data = store.getData();
			if (data === undefined) return;
			const selected = selectorRef.current(data);
			setValue((previous) => (previous !== undefined && equalsRef.current(previous, selected) ? previous : selected));
		};
		const stops = fields.map((field) => store.subscribe([field], update));
		stops.push(store.onReady(update));
		return () => {
			for (const stop of stops) stop();
		};
	}, [store, fieldsKey]);

	return value;
}
