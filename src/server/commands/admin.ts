import { Components } from "@flamework/components";
import { Dependency } from "@flamework/core";
import { Centurion, CenturionType, Command, CommandContext, CommandGuard, Guard, Register } from "@rbxts/centurion";
import { RunService } from "@rbxts/services";
import { CoinsWallet } from "server/features/coins/coins-wallet";
import { PlayerCharacter } from "server/services/player/player-character";
import { PlayerDataNode } from "server/services/player/player-data-node";

const ADMIN_IDS = new Set<number>([418255008]);

const isAdmin: CommandGuard = (ctx) => {
	if (!RunService.IsStudio() && !ADMIN_IDS.has(ctx.executor.UserId)) {
		ctx.error("Insufficient permission!");
		return false;
	}
	return true;
};

function formatValue(lines: string[], value: unknown, depth: number): void {
	const indent = "  ".rep(depth);
	if (typeIs(value, "table")) {
		for (const [k, v] of pairs(value as Record<string, unknown>)) {
			if (typeIs(v, "table")) {
				lines.push(`${indent}${k}:`);
				formatValue(lines, v, depth + 1);
			} else {
				lines.push(`${indent}${k}: ${tostring(v)}`);
			}
		}
	} else {
		lines.push(`${indent}${tostring(value)}`);
	}
}

@Register()
@Guard(isAdmin)
// eslint-disable-next-line @typescript-eslint/no-unused-vars -- registered via the @Register decorator
class AdminCommands {
	@Command({ name: "help", description: "List every dev command and its arguments" })
	help(ctx: CommandContext) {
		const lines: string[] = [];
		for (const command of Centurion.server().registry.getCommands()) {
			const args = (command.options.arguments ?? []).map((arg) => `<${arg.name}>`).join(" ");
			const usage = args === "" ? command.getPath().toString() : `${command.getPath().toString()} ${args}`;
			lines.push(`${usage}  - ${command.options.description ?? ""}`);
		}
		lines.sort();
		ctx.reply(lines.join("\n"));
	}

	@Command({
		name: "viewdata",
		description: "View a player's data",
		arguments: [{ name: "player", description: "The target player", type: CenturionType.Player }],
	})
	viewData(ctx: CommandContext, player: Player) {
		const dataNode = Dependency<Components>().getComponent<PlayerDataNode>(player);

		if (!dataNode) {
			ctx.error(`Player data not loaded for ${player.Name}`);
			return;
		}

		const lines: string[] = [`--- ${player.Name} ---`];
		formatValue(lines, dataNode.getData(), 0);
		ctx.reply(lines.join("\n"));
	}

	@Command({
		name: "setspeed",
		description: "Set a player's walk speed for this body and every respawn; omit the speed to reset",
		arguments: [
			{ name: "player", description: "The target player", type: CenturionType.Player },
			{
				name: "speed",
				description: "Studs per second; the default is StarterPlayer.CharacterWalkSpeed",
				type: CenturionType.Number,
				optional: true,
			},
		],
	})
	setSpeed(ctx: CommandContext, player: Player, speed?: number) {
		const character = Dependency<Components>().getComponent<PlayerCharacter>(player);
		if (!character) {
			ctx.error(`Player data not loaded for ${player.Name}`);
			return;
		}
		if (speed !== undefined && (speed < 0 || speed !== speed)) {
			ctx.error(`Rejected: speed must be a number of at least 0`);
			return;
		}

		character.setWalkSpeed(speed);
		ctx.reply(`${player.Name} walks at ${character.getWalkSpeed()} studs/s${speed === undefined ? " (default)" : ""}`);
	}

	// coins feature — remove alongside the coins folders.
	@Command({
		name: "givecoins",
		description: "Give coins to a player",
		arguments: [
			{ name: "player", description: "The target player", type: CenturionType.Player },
			{ name: "amount", description: "Number of coins", type: CenturionType.Number },
		],
	})
	giveCoins(ctx: CommandContext, player: Player, amount: number) {
		const wallet = Dependency<Components>().getComponent<CoinsWallet>(player);

		if (!wallet) {
			ctx.error(`Player data not loaded for ${player.Name}`);
			return;
		}

		wallet.addCoins(amount);
		ctx.reply(`Gave ${amount} coins to ${player.Name}`);
	}
}
