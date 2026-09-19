import { Controller, OnStart } from "@flamework/core";
import Replica, { ReplicaClient as ReplicaClientType } from "@rbxts/loleris-replica";
import { Players } from "@rbxts/services";
import { PLAYER_DATA_TOKEN } from "shared/types/player-data";
import type { PlayerData } from "shared/types/player-data";
import { PathSubscriptions } from "./path-subscriptions";
import type { DataChange, DataPath, PlayerDataStore } from "./player-data-store";

const ReplicaClient = Replica as ReplicaClientType;
/** The package exports no name for a client replica; take it from OnNew's listener. */
type ReplicaObject = Parameters<Parameters<ReplicaClientType["OnNew"]>[1]>[0];

/**
 * The client end of the profile mirror. Keeps the local player's one Replica
 * and dispatches each change by path, so a feature subscribes to the fields
 * it renders and nothing else. UI reaches it through PlayerDataContext
 * (UiController.mount supplies the provider), never Dependency<>().
 */
@Controller({})
export class PlayerDataController implements OnStart, PlayerDataStore {
	private replica?: ReplicaObject;
	private readonly subscriptions = new PathSubscriptions();
	private readyListeners: Array<(data: Readonly<PlayerData>) => void> = [];

	onStart(): void {
		ReplicaClient.OnNew(PLAYER_DATA_TOKEN, (replica) => {
			// The server subscribes only the owner, so this is a guard against a
			// fork that switches the node to Replicate(), not a filter.
			if (replica.Tags.PlayerId !== Players.LocalPlayer.UserId) return;

			this.replica = replica;
			// Replica has already applied the write to the mirror when this fires.
			replica.OnChange((action, path, value, detail) => {
				this.subscriptions.dispatch({ action, path, value, detail });
			});
			print("[anvil] player data replica received");

			const listeners = this.readyListeners;
			this.readyListeners = [];
			const data = replica.Data as unknown as Readonly<PlayerData>;
			for (const listener of listeners) {
				const [ok, err] = pcall(listener, data);
				if (!ok) warn(`[anvil] data ready listener failed: ${tostring(err)}`);
			}
		});

		ReplicaClient.RequestData();
	}

	public getData(): Readonly<PlayerData> | undefined {
		return this.replica?.Data as unknown as Readonly<PlayerData> | undefined;
	}

	public subscribe(path: DataPath, listener: (change: DataChange) => void): () => void {
		return this.subscriptions.subscribe(path, listener);
	}

	public onReady(listener: (data: Readonly<PlayerData>) => void): () => void {
		const data = this.getData();
		if (data !== undefined) {
			listener(data);
			return () => {};
		}
		this.readyListeners.push(listener);
		return () => {
			this.readyListeners = this.readyListeners.filter((other) => other !== listener);
		};
	}
}
