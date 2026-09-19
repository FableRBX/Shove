import { BaseComponent, Component } from "@flamework/components";
import Replica, { ReplicaServer as ReplicaServerType } from "@rbxts/loleris-replica";
import { PLAYER_DATA_TOKEN } from "shared/types/player-data";
import type { ArrayField, MapField, PlayerData } from "shared/types/player-data";
import { PlayerProfile } from "./player-profile";
import { PLAYER_LOADED_TAG } from "./player-tags";

const ReplicaServer = Replica as ReplicaServerType;
const PlayerDataToken = ReplicaServer.Token(PLAYER_DATA_TOKEN);

/**
 * A loaded profile's data, mirrored to its owning client through Replica.
 * Exists only while PlayerLoaded is on the player, so holding one means data
 * is ready.
 *
 * `set`, `setEntry`, `insertItem` and `removeItemAt` are the single write
 * seam. Nothing calls them from arbitrary code: each feature's per-player
 * component wraps them in operation-shaped mutators (CoinsWallet.addCoins),
 * which is where validation and change signals live.
 */
@Component({ tag: PLAYER_LOADED_TAG })
export class PlayerDataNode extends BaseComponent<{}, Player> {
	private readonly replica;
	private readyConnection?: RBXScriptConnection;

	constructor(profile: PlayerProfile) {
		super();

		this.replica = new ReplicaServer<PlayerData, { PlayerId: number }>({
			Token: PlayerDataToken,
			Data: profile.getProfile().Data,
			Tags: { PlayerId: this.instance.UserId },
		});

		// Subscribe only the owner: a profile is private, so no other client
		// receives it. Use Replicate() for state every client should see.
		//
		// Subscribe() is dropped (with a warning) if the client has not yet
		// called RequestData(), and the profile usually loads before the client
		// boots, so defer until Replica reports the player ready.
		if (ReplicaServer.ReadyPlayers.has(this.instance)) {
			this.replica.Subscribe(this.instance);
		} else {
			this.readyConnection = ReplicaServer.NewReadyPlayer.Connect((player) => {
				if (player !== this.instance) return;
				this.readyConnection?.Disconnect();
				this.readyConnection = undefined;
				this.replica.Subscribe(player);
			});
		}
	}

	public getData(): Readonly<PlayerData> {
		return this.replica.Data;
	}

	public set<K extends keyof PlayerData>(key: K, value: PlayerData[K]): void {
		this.replica.Set([key], value);
	}

	/**
	 * Writes one entry of a map field, replicating only that entry rather than
	 * the whole table. `undefined` removes the entry.
	 */
	public setEntry<K extends MapField, I extends keyof PlayerData[K] & string>(
		key: K,
		id: I,
		value: PlayerData[K][I] | undefined,
	): void {
		this.replica.Set([key, id], value);
	}

	/** Appends one item to an array field, replicating only the insert. */
	public insertItem<K extends ArrayField>(key: K, value: PlayerData[K][number]): void {
		this.replica.TableInsert([key], value);
	}

	/**
	 * Removes the item at a zero-based index from an array field, replicating
	 * only the remove. Replica and Luau count from one, so the index is shifted.
	 */
	public removeItemAt<K extends ArrayField>(key: K, index: number): void {
		this.replica.TableRemove([key], index + 1);
	}

	override destroy(): void {
		this.readyConnection?.Disconnect();
		this.replica.Destroy();
		super.destroy();
	}
}
