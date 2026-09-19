import { Controller, OnStart } from "@flamework/core";
import React from "@rbxts/react";
import { createPortal, createRoot, Root } from "@rbxts/react-roblox";
import { Players } from "@rbxts/services";
import { App } from "client/ui/app";
import { PlayerDataProvider } from "client/ui/player-data-context";
import { PlayerDataController } from "./player-data-controller";

export interface MountOptions {
	ignoreGuiInset?: boolean;
	displayOrder?: number;
}

/**
 * The one place UI roots are created. Every feature mounts through `mount`,
 * so the container, root, portal, ScreenGui and data provider live here once;
 * a feature still owns its UI, because the feature makes the call.
 */
@Controller({})
export class UiController implements OnStart {
	/** Every live root, so an unparented container is never left to the garbage collector. */
	private readonly roots = new Set<Root>();

	constructor(private readonly data: PlayerDataController) {}

	/** Mounts the App shell. */
	onStart(): void {
		this.mount("AnvilApp", <App />, { ignoreGuiInset: true });
	}

	/**
	 * Mounts a feature's UI: a root on an unparented Folder, and a portal to a
	 * ScreenGui named `name` in PlayerGui (ResetOnSpawn off, ZIndexBehavior
	 * Sibling) wrapped in PlayerDataProvider. Returns unmount.
	 */
	public mount(name: string, element: React.Element, options?: MountOptions): () => void {
		const playerGui = Players.LocalPlayer.WaitForChild("PlayerGui") as PlayerGui;

		// React roots take ownership of their container, so give the root a
		// Folder of its own and portal into PlayerGui rather than mounting on
		// it. The Folder stays unparented (the react-roblox idiom): nothing
		// renders into it, and PlayerGui would destroy it on respawn.
		const container = new Instance("Folder");
		container.Name = name;

		const root = createRoot(container);
		this.roots.add(root);
		root.render(
			<PlayerDataProvider store={this.data}>
				{createPortal(
					<screengui
						key={name}
						ResetOnSpawn={false}
						ZIndexBehavior={Enum.ZIndexBehavior.Sibling}
						IgnoreGuiInset={options?.ignoreGuiInset ?? false}
						DisplayOrder={options?.displayOrder ?? 0}
					>
						{element}
					</screengui>,
					playerGui,
				)}
			</PlayerDataProvider>,
		);

		return () => {
			this.roots.delete(root);
			root.unmount();
			container.Destroy();
		};
	}
}
