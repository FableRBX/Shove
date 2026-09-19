# anvil

A fork-per-game Roblox template: permanent infrastructure every future game
inherits by forking this repo.

## Language

**Spine**: The permanent infrastructure every fork inherits — lifecycle,
persistence, replication, networking, UI mount, testing.
_Avoid_: framework (that word means Flamework here), engine

**Satellite**: An opt-in package a fork adds for its genre; never required by
the spine.
_Avoid_: plugin, extension

**Service**: A Flamework `@Service` class on the server.

**Controller**: A Flamework `@Controller` class on the client; the Service's
client twin.

**Component**: A Flamework `@Component` class bound to a CollectionService tag.
Per-player state is components on the Player instance, bound to
`PlayerPending` (the session is loading) or `PlayerLoaded` (data is ready).

**Feature**: A deletable unit of gameplay spanning up to all three layers plus
its schema field, mutators, and network events. Deleting a feature is deleting
those and nothing else.

**Shared**: `src/shared/`, the client-visible surface: types, the network
contract, replica tokens. Clients can decompile it, so server rules, defaults,
and migrations never live there.

**Profile**: A player's persisted, versioned data document (ProfileStore).
One per player, loaded at join, released at leave.
_Avoid_: save, player data (as a noun)

**Migration**: A pure step upgrading a Profile from one version to the next;
migrations run in sequence at load, before the Replica exists.

**Mutator**: A typed, operation-shaped write method on a feature's per-player
component (`CoinsWallet.addCoins`, not `setCoins`), the only caller of
`PlayerDataNode`'s write seam (`set`, `setEntry`, `insertItem`,
`removeItemAt`). All other access is read-only.

**Intent**: A client→server event naming a requested action, never a resulting
state. The server decides the outcome.
_Avoid_: command, RPC

**State**: Server-owned data mirrored to clients through Replica. Clients read
it and never write it. Intents travel over Flamework networking; State travels
over Replica — never the reverse.
