import { BaseComponent, Component } from "@flamework/components";
import { OnStart } from "@flamework/core";
import { LeaderstatsService } from "server/services/leaderstats-service";
import { PLAYER_LOADED_TAG } from "server/services/player/player-tags";
import { CoinsWallet } from "./coins-wallet";

/** Mirrors the wallet into the player-list leaderstats column. */
@Component({ tag: PLAYER_LOADED_TAG })
export class CoinsLeaderstats extends BaseComponent<{}, Player> implements OnStart {
	private connection?: RBXScriptConnection;

	constructor(
		private readonly wallet: CoinsWallet,
		private readonly leaderstatsService: LeaderstatsService,
	) {
		super();
	}

	onStart(): void {
		const coins = this.leaderstatsService.addStat(this.instance, "Coins", this.wallet.getCoins());

		this.connection = this.wallet.coinsChanged.Connect((total) => {
			coins.Value = total;
		});
	}

	override destroy(): void {
		this.connection?.Disconnect();
		super.destroy();
	}
}
