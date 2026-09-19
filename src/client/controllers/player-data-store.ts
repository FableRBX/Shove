import type { PlayerData } from "shared/types/player-data";

/** A path into the mirror as Replica ships it: field, then entry id or Luau one-based item index. */
export type DataPath = ReadonlyArray<string | number>;

export type DataAction = "Set" | "SetValues" | "TableInsert" | "TableRemove";

/** One write, as Replica reports it after the mirror has been updated. */
export interface DataChange {
	action: DataAction;
	path: DataPath;
	/** Set: the new value (undefined removes). SetValues: the values table. TableInsert: the inserted item. TableRemove: the removed item. */
	value: unknown;
	/** Set: the old value. TableInsert and TableRemove: Replica's one-based index. */
	detail?: unknown;
}

/**
 * The client's view of the profile mirror. PlayerDataController implements it
 * over the Replica; hooks take it from PlayerDataContext, so UI can be
 * exercised with a fake.
 */
export interface PlayerDataStore {
	/** The live mirror, or undefined until it arrives. Never mutate it. */
	getData(): Readonly<PlayerData> | undefined;
	/** Fires for every change whose path overlaps `path`, after the mirror has been updated. Returns unsubscribe. */
	subscribe(path: DataPath, listener: (change: DataChange) => void): () => void;
	/** Fires once with the mirror: now if it has arrived, else when it does. Returns unsubscribe. */
	onReady(listener: (data: Readonly<PlayerData>) => void): () => void;
}
