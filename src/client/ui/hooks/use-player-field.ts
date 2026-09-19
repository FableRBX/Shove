import { useEffect, useState } from "@rbxts/react";
import { getAt, snapshot } from "client/controllers/data-path";
import type { PlayerDataStore } from "client/controllers/player-data-store";
import type { PlayerData } from "shared/types/player-data";
import { usePlayerDataStore } from "../player-data-context";

function readField<K extends keyof PlayerData>(store: PlayerDataStore, key: K): Readonly<PlayerData[K]> | undefined {
	const data = store.getData();
	return data === undefined ? undefined : (snapshot(getAt(data, [key])) as Readonly<PlayerData[K]>);
}

/**
 * The field, re-rendering only when it or anything beneath it changes. Tables
 * come back shallow-cloned. Undefined until the mirror arrives.
 */
export function usePlayerField<K extends keyof PlayerData>(key: K): Readonly<PlayerData[K]> | undefined {
	const store = usePlayerDataStore();
	const [value, setValue] = useState(() => readField(store, key));

	useEffect(() => {
		// Re-read in the effect too: a change between render and subscribe is not missed.
		const update = () => setValue(readField(store, key));
		const stopReady = store.onReady(update);
		const stopChanges = store.subscribe([key], update);
		return () => {
			stopReady();
			stopChanges();
		};
	}, [store, key]);

	return value;
}
