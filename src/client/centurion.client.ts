import { Centurion } from "@rbxts/centurion";
import { CenturionUI } from "@rbxts/centurion-ui";

const client = Centurion.client();
client
	.start()
	.then(() => {
		CenturionUI.start(client, { activationKeys: [Enum.KeyCode.F2] });
	})
	.catch((err) => warn("[push-a-giant] Centurion client failed to start:", err));
