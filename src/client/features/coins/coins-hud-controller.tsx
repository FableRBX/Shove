import { Controller, OnStart } from "@flamework/core";
import React from "@rbxts/react";
import { UiController } from "client/controllers/ui-controller";
import { CoinsHud } from "./coins-hud";

// Features mount their own UI so deleting the feature deletes its interface.
@Controller({})
export class CoinsHudController implements OnStart {
	constructor(private readonly ui: UiController) {}

	onStart(): void {
		this.ui.mount("CoinsHud", <CoinsHud />);
	}
}
