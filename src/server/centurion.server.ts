import { Centurion } from "@rbxts/centurion";

const server = Centurion.server();
server.registry.load(script.Parent!.FindFirstChild("commands")!);
server.start();
