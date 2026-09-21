import React, { createContext, useContext } from "@rbxts/react";
import type { PlayerDataStore } from "client/controllers/player-data-store";

export const PlayerDataContext = createContext<PlayerDataStore | undefined>(undefined);

export function PlayerDataProvider(props: { store: PlayerDataStore; children?: React.ReactNode }): React.Element {
	return <PlayerDataContext.Provider value={props.store}>{props.children}</PlayerDataContext.Provider>;
}

/**
 * The store from context. Throws outside a provider: every root goes through
 * UiController.mount, which supplies one, so a hook never reaches for
 * Dependency<>() and can be exercised with a fake store.
 */
export function usePlayerDataStore(): PlayerDataStore {
	const store = useContext(PlayerDataContext);
	if (store === undefined) throw "[push-a-giant] no PlayerDataProvider: mount UI through UiController";
	return store;
}
