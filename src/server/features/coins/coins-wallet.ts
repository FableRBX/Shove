import { BaseComponent, Component } from "@flamework/components";
import Signal from "@rbxts/signal";
import { PlayerDataNode } from "server/services/player/player-data-node";
import { PLAYER_LOADED_TAG } from "server/services/player/player-tags";
import { canRequestCoin } from "./can-request-coin";
import { COIN_REQUEST_COOLDOWN } from "./coins-config";

/**
 * The coins feature's per-player state and its only write path. Mutators are
 * operation-shaped: they validate, write through PlayerDataNode.set, and
 * announce the change.
 */
@Component({ tag: PLAYER_LOADED_TAG })
export class CoinsWallet extends BaseComponent<{}, Player> {
	public readonly coinsChanged = new Signal<(total: number) => void>();
	private lastRequestAt?: number;

	constructor(private readonly dataNode: PlayerDataNode) {
		super();
	}

	public getCoins(): number {
		return this.dataNode.getData().Coins;
	}

	public addCoins(amount: number): void {
		const total = this.getCoins() + amount;
		this.dataNode.set("Coins", total);
		this.coinsChanged.Fire(total);
	}

	/** The requestCoin intent. The server decides; invalid requests are dropped. */
	public requestCoin(): void {
		const now = os.clock();
		if (!canRequestCoin(this.lastRequestAt, now, COIN_REQUEST_COOLDOWN)) return;

		this.lastRequestAt = now;
		this.addCoins(1);
	}

	override destroy(): void {
		this.coinsChanged.Destroy();
		super.destroy();
	}
}
