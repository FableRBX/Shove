import { Flamework } from "@flamework/core";

Flamework.addPaths("src/server/services");
Flamework.addPaths("src/server/features");

Flamework.ignite();

print("[push-a-giant] server ignited");
