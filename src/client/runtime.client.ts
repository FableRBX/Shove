import { Flamework } from "@flamework/core";

Flamework.addPaths("src/client/controllers");
Flamework.addPaths("src/client/features");

Flamework.ignite();

print("[anvil] client ignited");
