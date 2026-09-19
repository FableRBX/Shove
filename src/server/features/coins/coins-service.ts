import { Components } from "@flamework/components";
import { OnStart, Service } from "@flamework/core";
import { Events } from "server/network";
import { CoinsWallet } from "./coins-wallet";

/**
 * Routes the requestCoin intent to the player's wallet. No wallet means the
 * profile is not loaded yet, so the intent is dropped.
 */
@Service({})
export class CoinsService implements OnStart {
	constructor(private readonly components: Components) {}

	onStart(): void {
		Events.requestCoin.connect((player) => this.components.getComponent<CoinsWallet>(player)?.requestCoin());
	}
}
