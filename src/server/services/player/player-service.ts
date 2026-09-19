import { OnStart, Service } from "@flamework/core";
import ProfileStore from "@rbxts/profile-store";
import { CollectionService, Players, RunService } from "@rbxts/services";
import type { PlayerData } from "shared/types/player-data";
import { DEFAULT_PLAYER_DATA } from "./player-data-defaults";
import { PLAYER_LOADED_TAG, PLAYER_PENDING_TAG } from "./player-tags";
import { PROFILE_LOAD_TIMEOUT, shouldCancelProfileLoad } from "./session-policy";

type PlayerStore = Omit<ProfileStore.Store<PlayerData>, "Mock">;

/**
 * Owns the one singleton in the player spine, the ProfileStore store, and
 * turns joins and leaves into tags. Everything per-player is a component on
 * the Player instance (ADR 0008).
 */
@Service({})
export class PlayerService implements OnStart {
	private store!: PlayerStore;

	onStart(): void {
		const liveStore = ProfileStore.New<PlayerData>("PlayerData", DEFAULT_PLAYER_DATA);
		// Studio never touches live keys, even with API access enabled. Mock
		// profiles are forgotten when Play stops.
		this.store = RunService.IsStudio() ? liveStore.Mock : liveStore;

		ProfileStore.OnError.Connect((message, storeName, profileKey) =>
			warn(`[anvil] ProfileStore error: ${message} [${storeName}/${profileKey}]`),
		);
		ProfileStore.OnOverwrite.Connect((storeName, profileKey) =>
			warn(`[anvil] ProfileStore overwrote non-profile data at ${storeName}/${profileKey}`),
		);
		ProfileStore.OnCriticalToggle.Connect((isCritical) =>
			warn(`[anvil] ProfileStore critical state ${isCritical ? "entered" : "cleared"}`),
		);

		// Declared in default.project.json so it applies before any script runs;
		// re-asserted here in case a fork builds without that property.
		Players.CharacterAutoLoads = false;

		Players.PlayerAdded.Connect((player) => CollectionService.AddTag(player, PLAYER_PENDING_TAG));

		// Loaded comes off first so feature components and the character are
		// destroyed before PlayerProfile ends the session.
		Players.PlayerRemoving.Connect((player) => {
			CollectionService.RemoveTag(player, PLAYER_LOADED_TAG);
			CollectionService.RemoveTag(player, PLAYER_PENDING_TAG);
		});

		for (const player of Players.GetPlayers()) {
			CollectionService.AddTag(player, PLAYER_PENDING_TAG);
		}
	}

	/**
	 * Starts a session for the player's profile. Yields. Returns undefined when
	 * the player left, the timeout passed, the server is closing, or the same
	 * key is being loaded concurrently.
	 */
	public startSession(player: Player): ProfileStore.Profile<PlayerData> | undefined {
		const startedAt = os.clock();
		// The typings promise a Profile; the Luau returns nil in the cases above.
		return this.store.StartSessionAsync(`${player.UserId}`, {
			Cancel: () =>
				shouldCancelProfileLoad(player.IsDescendantOf(Players), os.clock() - startedAt, PROFILE_LOAD_TIMEOUT),
		}) as ProfileStore.Profile<PlayerData> | undefined;
	}
}
