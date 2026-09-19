import { useEffect, useState } from "@rbxts/react";
import { getAt, snapshot } from "client/controllers/data-path";
import type { PlayerDataStore } from "client/controllers/player-data-store";
import type { MapField, PlayerData } from "shared/types/player-data";
import { usePlayerDataStore } from "../player-data-context";

function readEntry<K extends MapField>(
	store: PlayerDataStore,
	key: K,
	id: string,
): Readonly<PlayerData[K][string]> | undefined {
	const data = store.getData();
	return data === undefined ? undefined : (snapshot(getAt(data, [key, id])) as Readonly<PlayerData[K][string]>);
}

/**
 * One entry of a map field, re-rendering on a write to that entry or to the
 * whole field. Undefined until the mirror arrives or when the entry is absent.
 */
export function usePlayerEntry<K extends MapField>(key: K, id: string): Readonly<PlayerData[K][string]> | undefined {
	const store = usePlayerDataStore();
	const [value, setValue] = useState(() => readEntry(store, key, id));

	useEffect(() => {
		const update = () => setValue(readEntry(store, key, id));
		const stopReady = store.onReady(update);
		const stopChanges = store.subscribe([key, id], update);
		return () => {
			stopReady();
			stopChanges();
		};
	}, [store, key, id]);

	return value;
}
