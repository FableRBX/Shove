import { BaseComponent, Component } from "@flamework/components";
import { OnStart } from "@flamework/core";
import Signal from "@rbxts/signal";
import { Players, StarterPlayer } from "@rbxts/services";
import { PLAYER_LOADED_TAG } from "./player-tags";

/**
 * Owns a player's character lifecycle. Bound to PlayerLoaded, so the first
 * spawn cannot precede the profile (ADR 0006). CharacterAutoLoads is off, so
 * the engine neither spawns nor respawns; this component does both.
 *
 * Consumers use both paths: read getCharacter() for a body that already
 * exists, and connect characterAdded for the next one.
 *
 * Walk speed is a per-player setting this component owns: it is applied to
 * every body as it arrives, so a respawn never resets it.
 */
@Component({ tag: PLAYER_LOADED_TAG })
export class PlayerCharacter extends BaseComponent<{}, Player> implements OnStart {
	public readonly characterAdded = new Signal<(character: Model) => void>();

	private character?: Model;
	private characterConnection?: RBXScriptConnection;
	private diedConnection?: RBXScriptConnection;
	private destroyed = false;
	/** Walk speed applied to every body; undefined means StarterPlayer's default. */
	private walkSpeed?: number;

	onStart(): void {
		this.characterConnection = this.instance.CharacterAdded.Connect((character) => this.onCharacterAdded(character));
		// No character can precede this component while CharacterAutoLoads is
		// off, but a fork that turns it back on must not miss the first one.
		if (this.instance.Character) this.onCharacterAdded(this.instance.Character);

		// Deferred so the other PlayerLoaded components construct before the
		// first body exists, and because LoadCharacterAsync yields.
		task.defer(() => this.spawn());
	}

	public getCharacter(): Model | undefined {
		return this.character;
	}

	/**
	 * Sets the walk speed of this player's current body and every one that
	 * spawns after it. Pass undefined to return to StarterPlayer's default.
	 */
	public setWalkSpeed(speed: number | undefined): void {
		this.walkSpeed = speed;
		const humanoid = this.character?.FindFirstChildOfClass("Humanoid");
		if (humanoid) this.applyWalkSpeed(humanoid);
	}

	public getWalkSpeed(): number {
		return this.walkSpeed ?? StarterPlayer.CharacterWalkSpeed;
	}

	/** Spawns a character. The first spawn and every respawn run through here. */
	public spawn(): void {
		if (this.destroyed || !this.instance.IsDescendantOf(Players)) return;

		const [ok, err] = pcall(() => this.instance.LoadCharacterAsync());
		if (!ok) warn(`[push-a-giant] LoadCharacterAsync failed for ${this.instance.Name}: ${tostring(err)}`);
	}

	private onCharacterAdded(character: Model): void {
		this.character = character;
		this.diedConnection?.Disconnect();

		const humanoid =
			character.FindFirstChildOfClass("Humanoid") ?? (character.WaitForChild("Humanoid", 5) as Humanoid | undefined);
		if (humanoid === undefined) {
			warn(`[push-a-giant] character without Humanoid for ${this.instance.Name}`);
			return;
		}

		this.diedConnection = humanoid.Died.Connect(() => this.scheduleRespawn());
		this.applyWalkSpeed(humanoid);
		this.characterAdded.Fire(character);
	}

	private applyWalkSpeed(humanoid: Humanoid): void {
		humanoid.WalkSpeed = this.getWalkSpeed();
	}

	private scheduleRespawn(): void {
		task.delay(Players.RespawnTime, () => {
			if (this.destroyed || !this.instance.IsDescendantOf(Players)) return;

			const humanoid = this.instance.Character?.FindFirstChildOfClass("Humanoid");
			if (humanoid !== undefined && humanoid.Health > 0) return; // already alive again

			this.spawn();
		});
	}

	override destroy(): void {
		this.destroyed = true;
		this.characterConnection?.Disconnect();
		this.diedConnection?.Disconnect();
		this.characterAdded.Destroy();
		super.destroy();
	}
}
