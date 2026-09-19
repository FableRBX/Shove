# 0007 — `src/shared/` is the client-visible surface only

**Context.** Everything under `src/shared/` replicates to every client and
can be decompiled. The original layout put all pure logic there because the
test place mounted only the shared tree, which meant server rules
(validation, cooldowns), profile defaults, migrations, and the session policy
shipped to clients.

**Decision.** Shared holds only what the client must see: types, the network
contract, replica tokens, constants the client renders with. Pure server
logic lives in `src/server/` beside its consumer (`util/` for helpers); pure
client logic lives in `src/client/`. The test place mounts all three trees at
their game-place paths with runtime scripts excluded, and Jest's `roots` span
them, so specs sit beside the code in any layer. The game place excludes
`*.spec` files and the Jest config.

**Consequences.** Less of the game is readable from a client. A feature's
`shared/` folder is optional and often absent. Defaults and migrations live
two files away from the schema interface rather than beside it.
