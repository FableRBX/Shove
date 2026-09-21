# Push a Giant

A Roblox strength simulator where players do push-ups, grow into giants, and
click through dramatic shoving contests to throw increasingly enormous
opponents off cliffs. Built with [roblox-ts](https://roblox-ts.com/) and
[Flamework](https://flamework.fireboltofdeath.dev/) on the `anvil` template,
which supplies the spine (persistence, replication, networking, UI mount,
testing). The design is in `docs/push-a-giant-gdd.md`.

## Stack

- **roblox-ts** — TypeScript → Luau compiler
- **Flamework** — services/controllers with DI and typed networking
- **ProfileStore** — player data persistence with session locking
- **loleris-replica** — server→client state replication
- **@rbxts/react** — UI (React Lua)
- **Centurion** — dev command console (F2)
- **@rbxts/jest** — in-engine Jest tests
- **Utilities** — `@rbxts/t` (runtime type checks), `@rbxts/ripple` +
  `@rbxts/pretty-react-hooks` (springs and React hooks), `@rbxts/object-utils`,
  `@rbxts/set-timeout`, `@rbxts/sift` (immutable data helpers)

## Getting started

```sh
rokit install         # pins Rojo, run-in-roblox, Lune
# Node 24 LTS (see .node-version); npm refuses older versions.
npm install
npm run test:setup    # one-time: enables Studio's FFlagEnableLoadModule for Jest
npm run assemble      # compile + build push-a-giant.rbxl
npm run studio        # assemble, then open push-a-giant.rbxl in a new Studio instance
npm test              # run the in-engine test suite
npm run lint          # eslint + prettier check (npm run format to fix)
```

Press Play in the Studio window that opened: you should see `[push-a-giant] server ignited`,
`[push-a-giant] client ignited`, `[push-a-giant] profile loaded for <you>`, then your character
spawns and a coins HUD is wired end-to-end (button → intent → validation →
mutator → Replica → React). Studio uses ProfileStore's mock store, so coins reset
between Play sessions.

## Building gameplay

Gameplay is built as features: pure logic beside the layer that owns it
(server rules in `src/server/features/<name>/`, presentation in
`src/client/features/<name>/`), specs beside the code, thin
services/controllers around them. `src/shared/` carries only what the client
must see. The example `coins` feature from the template shows every seam; see
`CLAUDE.md` for the feature deletion contract.

Conventions and invariants: `CLAUDE.md`. Vocabulary: `CONTEXT.md`.
Decisions: `docs/adr/`.
