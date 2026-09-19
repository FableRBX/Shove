import React, { useCallback } from "@rbxts/react";
import { Events } from "client/network";
import { usePlayerField } from "client/ui/hooks/use-player-field";

export function CoinsHud() {
	const coins = usePlayerField("Coins");

	const onRequestCoin = useCallback(() => {
		Events.requestCoin.fire();
	}, []);

	if (coins === undefined) return <></>;

	return (
		<frame
			key="CoinsPanel"
			AnchorPoint={new Vector2(0.5, 0)}
			Position={UDim2.fromScale(0.5, 0.02)}
			Size={UDim2.fromOffset(220, 90)}
			BackgroundColor3={Color3.fromRGB(30, 30, 30)}
			BackgroundTransparency={0.2}
		>
			<uicorner CornerRadius={new UDim(0, 8)} />
			<uilistlayout
				SortOrder={Enum.SortOrder.LayoutOrder}
				Padding={new UDim(0, 6)}
				HorizontalAlignment={Enum.HorizontalAlignment.Center}
				VerticalAlignment={Enum.VerticalAlignment.Center}
			/>
			<textlabel
				key="Count"
				LayoutOrder={1}
				Text={`Coins: ${coins}`}
				TextColor3={new Color3(1, 1, 1)}
				TextSize={20}
				BackgroundTransparency={1}
				Size={UDim2.fromOffset(200, 28)}
			/>
			<textbutton
				key="GetCoin"
				LayoutOrder={2}
				Text="Get Coin"
				TextSize={18}
				TextColor3={new Color3(1, 1, 1)}
				BackgroundColor3={Color3.fromRGB(0, 120, 215)}
				Size={UDim2.fromOffset(120, 32)}
				Event={{ Activated: onRequestCoin }}
			>
				<uicorner CornerRadius={new UDim(0, 6)} />
			</textbutton>
		</frame>
	);
}
