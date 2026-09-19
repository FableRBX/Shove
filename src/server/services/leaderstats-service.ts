import { Service } from "@flamework/core";

@Service({})
export class LeaderstatsService {
	public addStat(player: Player, name: string, initial: number): IntValue {
		const folder = this.getOrCreateFolder(player);

		const existing = folder.FindFirstChild(name);
		if (existing?.IsA("IntValue")) {
			warn(`[anvil] leaderstat ${name} already exists for ${player.Name}`);
			return existing;
		}

		const value = new Instance("IntValue");
		value.Name = name;
		value.Value = initial;
		value.Parent = folder;
		return value;
	}

	private getOrCreateFolder(player: Player): Folder {
		const existing = player.FindFirstChild("leaderstats");
		if (existing?.IsA("Folder")) return existing;

		const folder = new Instance("Folder");
		folder.Name = "leaderstats";
		folder.Parent = player;
		return folder;
	}
}
