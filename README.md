# anvil

A fork-per-game Roblox template built with [roblox-ts](https://roblox-ts.com/)
and [Flamework](https://flamework.fireboltofdeath.dev/). Fork it, rename it,
ship a game; the spine (persistence, replication, networking, UI mount,
testing) comes along.

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
npm run assemble      # compile + build anvil.rbxl
npm run studio        # assemble, then open anvil.rbxl in a new Studio instance
npm test              # run the in-engine test suite
npm run lint          # eslint + prettier check (npm run format to fix)
```

Press Play in the Studio window that opened: you should see `[anvil] server ignited`,
`[anvil] client ignited`, `[anvil] profile loaded for <you>`, then your character
spawns and a coins HUD is wired end-to-end (button → intent → validation →
mutator → Replica → React). Studio uses ProfileStore's mock store, so coins reset
between Play sessions.

## Forking a new game

1. Fork/copy this repo; rename in `package.json`, `default.project.json`,
   `test.project.json`, `README.md`.
2. Keep or delete the example `coins` feature (see `CLAUDE.md` for the
   deletion contract).
3. Build gameplay as features: pure logic beside the layer that owns it
   (server rules in `src/server/features/<name>/`, presentation in
   `src/client/features/<name>/`), specs beside the code, thin
   services/controllers around them. `src/shared/` carries only what the
   client must see.

Conventions and invariants: `CLAUDE.md`. Vocabulary: `CONTEXT.md`.
Decisions: `docs/adr/`.
