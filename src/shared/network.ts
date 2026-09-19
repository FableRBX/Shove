import { Networking } from "@flamework/networking";

interface ClientToServerEvents {
	// coins feature: ask the server for one coin. The server decides.
	requestCoin(): void;
}

interface ServerToClientEvents {}

interface ClientToServerFunctions {}

interface ServerToClientFunctions {}

export const GlobalEvents = Networking.createEvent<ClientToServerEvents, ServerToClientEvents>();
export const GlobalFunctions = Networking.createFunction<ClientToServerFunctions, ServerToClientFunctions>();
