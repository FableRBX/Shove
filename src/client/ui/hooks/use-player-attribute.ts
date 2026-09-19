import { useEffect, useState } from "@rbxts/react";
import { Players } from "@rbxts/services";

/**
 * An attribute on the local Player, re-rendering when the server writes it.
 * Undefined until it is set. This is the channel for per-player state that
 * is not part of the profile (a cap, a cooldown, a server-computed figure):
 * the server sets the attribute, the client only reads it.
 */
export function usePlayerAttribute(name: string): AttributeValue | undefined {
	const player = Players.LocalPlayer;
	const [value, setValue] = useState(() => player.GetAttribute(name));

	useEffect(() => {
		const update = () => setValue(player.GetAttribute(name));
		update();
		const connection = player.GetAttributeChangedSignal(name).Connect(update);
		return () => connection.Disconnect();
	}, [name]);

	return value;
}
