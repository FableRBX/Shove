import { BaseComponent, Component } from "@flamework/components";
import { OnStart } from "@flamework/core";
import ProfileStore from "@rbxts/profile-store";
import { CollectionService, Players } from "@rbxts/services";
import type { PlayerData } from "shared/types/player-data";
import { migrate } from "./migrations";
import { PlayerService } from "./player-service";
import { PLAYER_LOADED_TAG, PLAYER_PENDING_TAG } from "./player-tags";
import { shouldKickOnSessionEnd } from "./session-policy";

const LOAD_FAILED_MESSAGE = "Your data failed to load - please rejoin";
const SESSION_STOLEN_MESSAGE = "Your data has been loaded on another server - please rejoin";

/**
 * Owns a player's ProfileStore session from join to leave. Bound to
 * PlayerPending; adds PlayerLoaded once the profile is in memory, which is
 * what constructs PlayerDataNode, PlayerCharacter, and feature components.
 */
@Component({ tag: PLAYER_PENDING_TAG })
export class PlayerProfile extends BaseComponent<{}, Player> implements OnStart {
	private profile?: ProfileStore.Profile<PlayerData>;
	private ending = false;
	private destroyed = false;

	constructor(private readonly playerService: PlayerService) {
		super();
	}

	onStart(): void {
		// Flamework runs onStart synchronously inside component setup, so the
		// yielding load gets its own thread.
		task.spawn(() => this.load());
	}

	/** The loaded profile. Only components bound to PlayerLoaded may assume it exists. */
	public getProfile(): ProfileStore.Profile<PlayerData> {
		assert(this.profile, `[push-a-giant] profile not loaded for ${this.instance.Name}`);
		return this.profile;
	}

	public isLoaded(): boolean {
		return this.profile !== undefined;
	}

	/** True once this server has started ending the session itself. */
	public isEnding(): boolean {
		return this.ending;
	}

	private load(): void {
		const player = this.instance;
		const profile = this.playerService.startSession(player);

		// A player who left mid-load has already had this component destroyed.
		if (this.destroyed || !player.IsDescendantOf(Players)) {
			profile?.EndSession();
			return;
		}

		if (profile === undefined) {
			// Never substitute default data over a failed load; rejoining is the retry.
			warn(`[push-a-giant] profile failed to load for ${player.Name}`);
			player.Kick(LOAD_FAILED_MESSAGE);
			return;
		}

		// Nothing below yields. If any of it throws, the session still ends and
		// the player is told to rejoin.
		const [ok, err] = pcall(() => {
			profile.Reconcile();
			profile.AddUserId(player.UserId);
			// A profile that is behind comes back as a migrated copy; a current
			// one comes back as-is. A failing step leaves profile.Data untouched.
			profile.Data = migrate(profile.Data);
		});
		if (!ok) {
			warn(`[push-a-giant] profile setup failed for ${player.Name}: ${tostring(err)}`);
			profile.EndSession();
			player.Kick(LOAD_FAILED_MESSAGE);
			return;
		}

		// Fires on a steal by another server, on our own EndSession, and on
		// shutdown; only the steal deserves a kick.
		profile.OnSessionEnd.Connect(() => {
			const kick = shouldKickOnSessionEnd({
				intentional: this.ending,
				serverClosing: ProfileStore.IsClosing,
				playerPresent: player.IsDescendantOf(Players),
			});
			if (kick) player.Kick(SESSION_STOLEN_MESSAGE);
		});

		this.profile = profile;
		CollectionService.AddTag(player, PLAYER_LOADED_TAG);
		print(`[push-a-giant] profile loaded for ${player.Name}`);
	}

	override destroy(): void {
		this.destroyed = true;
		// Mark before ending so the session-end handler knows this is not a steal.
		this.ending = true;
		this.profile?.EndSession();
		super.destroy();
	}
}
