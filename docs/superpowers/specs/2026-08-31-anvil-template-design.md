# anvil — fork-per-game roblox-ts template

**Date:** 2026-08-31
**Status:** Implemented

## Purpose

`anvil` is a template repository from which every future Roblox game starts as a
fork. It contains the permanent infrastructure — the **spine** — that any game
needs: lifecycle, persistence, replication, networking, UI mount, and testing.
Because every fork inherits this code, invariants here outrank any individual
feature: a mistake in the spine cannot be un-shipped from games already forked.

`anvil` succeeds the Luau `seed` project as a clean-slate design for the roblox-ts
ecosystem, cherry-picking seed's philosophy (spine/satellite split, intent/state
split, typed mutators, deletable features) while adopting the stack proven in
the adjacent `Hatch` project.

## Success criteria

- The template always boots to a working, empty game: `npm run build` compiles
  with zero errors, the place opens in Studio, a player joins, their profile
  loads, and the example HUD renders.
- A fork can delete the example feature by deleting its feature folders,
  its schema field, its network event (`requestCoin`), and its admin command
  (`givecoins`) — and nothing else. The build stays green afterward. (Proven
  by the deletion drill, 2026-09-01, and again 2026-09-02 after the
  migrations spec was re-decoupled from the coins field; the `PlayerDataNode`
  members it once required moved into the feature's own component on
  2026-09-02.)
- `npm test` runs the in-engine Jest suite and passes.
- Every architectural decision made here is recorded as an ADR.

## Distribution model

- Template repo, git-initialized, forked per game. No published packages, no
  package versioning.
- Improvements flow forward by forking fresh; a live game can pull spine
  improvements with `git merge` from the template remote when it chooses to.
- The spine ships as ordinary source files the fork may edit — transparency
  over enforcement.

## Toolchain

| Concern | Choice |
|---|---|
| Language | TypeScript via **roblox-ts 3.0** (stable), strict mode |
| Framework transformer | **rbxts-transformer-flamework** |
| Tool pinning | **Rokit**: Rojo, Lune, run-in-roblox |
| Lint/format | **ESLint 9 flat config** + typescript-eslint 8 + eslint-plugin-roblox-ts + Prettier |
| Scripts | `build`, `watch`, `lint`, `test` |
| Dev loop | `rojo-dev-loop` skill (build → open Studio → serve) |

## Dependencies

Runtime:

- `@flamework/core`, `@flamework/components`, `@flamework/networking`
- `@rbxts/profile-store` — player data persistence with session locking
- `@rbxts/loleris-replica` — server→client state replication
- `@rbxts/react`, `@rbxts/react-roblox` — UI
- `@rbxts/signal`
- `@rbxts/centurion`, `@rbxts/centurion-ui` — dev command console
- `@rbxts/services`

Dev:

- `roblox-ts`, `rbxts-transformer-flamework`, `typescript`
- `@rbxts/compiler-types`, `@rbxts/types`
- `@rbxts/jest`, `@rbxts/jest-globals` — in-engine testing
- ESLint/Prettier toolchain as above

## Layout

Layer-first at the Rojo boundary, feature-first within:

```
src/
  client/
    controllers/           # Flamework @Controller classes
      player-data-controller.ts
      app-controller.ts    # mounts the React root
    ui/
      app.tsx              # React root component
      hooks/
        use-player-data.ts # Replica → React bridge
    features/
      coins/               # client half of the example slice (HUD)
    network.ts             # client handle to GlobalEvents/Functions
    centurion.client.ts
    runtime.client.ts      # Flamework ignition
  server/
    services/
      player/
        player-service.ts   # the store + the two tags
        player-tags.ts
        player-profile.ts   # PlayerPending component: the session
        player-data-node.ts # PlayerLoaded component: Replica + set seam
        player-character.ts # PlayerLoaded component: spawn/respawn
        session-policy.ts   # pure session decisions + spec
        migrations.ts      # LATEST_VERSION, migrate + spec
        player-data-defaults.ts
    features/
      coins/               # server half of the example slice: intent
                           # router, wallet + leaderstats components,
                           # pure rule logic + *.spec.ts
    commands/              # Centurion commands
    util/                  # pure server helpers + specs
    network.ts
    centurion.server.ts
    runtime.server.ts
  shared/                  # client-visible surface only (ADR 0007)
    network.ts             # Flamework event/function interfaces
    types/
      player-data.ts       # PlayerData interface + replica token
    features/              # only what both layers need; often empty
default.project.json       # game place (excludes *.spec and jest config)
test.project.json          # test place (all three trees, Jest runner)
```

## The spine

### PlayerService (server)

Owns the one singleton in the player spine, the ProfileStore store, and turns
joins and leaves into tags (ADR 0008):

- On start: create the store (`ProfileStore.Mock` in Studio so Play never
  touches live keys), log ProfileStore's error, overwrite, and critical-state
  signals, force `CharacterAutoLoads` off, add `PlayerPending` on
  `PlayerAdded` and for players already present, and on `PlayerRemoving`
  remove `PlayerLoaded` then `PlayerPending`.
- `startSession(player)`: `StartSessionAsync` with a `Cancel` that stops on
  leave or after `PROFILE_LOAD_TIMEOUT`; returns undefined where the Luau
  returns nil.

### PlayerProfile (server component, `PlayerPending`)

- Owns the session from join to leave. `onStart` spawns the load, because
  Flamework runs `onStart` synchronously inside component setup:
  `startSession` → if destroyed or the player left during the yield, end the
  session → a nil profile kicks with a rejoin message (default data is never
  substituted) → `Reconcile()` → `AddUserId` → `migrate` (a behind profile
  comes back as a migrated copy, a current one as-is), inside a pcall that
  ends the session and kicks on failure → connect `OnSessionEnd` → add
  `PlayerLoaded`.
- `OnSessionEnd` → kick with a "data loaded elsewhere" message only on a real
  steal (`shouldKickOnSessionEnd`: not our own end, not a shutdown, player
  still present).
- `destroy()` marks the end intentional and ends the session; Flamework calls
  it when `PlayerPending` comes off.

### PlayerDataNode (server component, `PlayerLoaded`)

- Injects `PlayerProfile` and creates a Replica over `profile.Data`, tagged
  with the player's UserId and subscribed to that player only. Exists only
  while the profile is loaded, so holding one means data is ready.
- **`set<K>(key, value)` is the single write seam.** Only a feature's
  per-player component calls it, from operation-shaped mutators
  (`CoinsWallet.addCoins`) that validate and announce the change. Nothing
  else writes.
- All other access is `getData(): Readonly<PlayerData>`.
- `destroy()` tears down the replica.

### PlayerCharacter (server component, `PlayerLoaded`)

- Owns spawn, respawn (`Players.RespawnTime`), `getCharacter()`, and the
  `characterAdded` signal (ADR 0006). Defers the first spawn one step so
  sibling components construct before a body exists.

### PlayerData schema (shared)

Minimal template schema demonstrating each pattern a fork will extend:

```ts
interface PlayerData {
  Version: number;                    // migration anchor
  Coins: number;                      // example currency (owned by the example slice)
  Settings: { [key: string]: boolean };
}
```

- Additive changes rely on `Reconcile()` against `DEFAULT_PLAYER_DATA`.
- Shape-changing migrations: bump `Version`, run ordered pure migration steps
  at load before the Replica is created. The mechanism ships (a
  `migrations.ts` with an ordered list, applied in `PlayerService`), with one
  documented no-op example.

### Networking (shared)

- `shared/network.ts` defines `ClientToServerEvents`, `ServerToClientEvents`,
  and function interfaces; `Networking.createEvent` / `createFunction` export
  `GlobalEvents` / `GlobalFunctions`; client and server get thin
  `client/network.ts` / `server/network.ts` handles (Hatch's pattern).
- **Invariant: the client sends intent, the server decides.** Event names are
  requested actions (`buyItem`), never resulting states.
- Flamework's generated runtime type guards validate every payload; handlers
  additionally validate game rules and silently drop invalid intents.

### Client data layer

- `PlayerDataController` (@Controller): requests/receives the player's Replica,
  exposes `getData()`, a `dataChanged` signal, and per-path observation for
  the UI bridge.

### UI mount

- `AppController` (@Controller) creates a `ScreenGui`, mounts the React root
  (`app.tsx`) via `createRoot` on start.
- `use-player-data.ts` hook subscribes to `PlayerDataController` and re-renders
  on replica changes. UI conventions follow the `roblox-react-ui` skill.

### Centurion

- Wired on both sides with the default UI on the client, gated to Studio and
  an allowlist of admin UserIds.
- One example command in `server/commands/` (`coins give <player> <amount>`)
  calling the same mutator path as gameplay.

### Flamework components

- `@flamework/components` is the per-player pattern, not just an example:
  the spine's `PlayerProfile`, `PlayerDataNode`, and `PlayerCharacter` are
  components on the Player instance, and each feature's per-player state is a
  component bound to `PlayerLoaded` (`CoinsWallet`, `CoinsLeaderstats`).
  Components inject singletons and sibling components; intent handlers reach
  a player's component through `Components.getComponent` (ADR 0008).

### LeaderstatsService (server)

- Spine owner of the Roblox leaderboard: lazily creates the per-player
  `leaderstats` folder on first use; features contribute stats via
  `addStat(player, name, initial): IntValue`. No feature owns the folder,
  since several features may contribute stats.

## Example vertical slice: coins

Deliberately trivial living documentation exercising every seam:

1. React HUD shows the coin count (`use-player-data`) and a button.
2. Button fires the `requestCoin` intent through `GlobalEvents`.
3. `CoinsService` routes the intent to the player's `CoinsWallet` component
   (undefined means data is not loaded: dropped). The wallet validates — a
   simple per-player cooldown, demonstrating where game-rule validation
   lives — and calls its own `addCoins(1)`, which writes through
   `PlayerDataNode.set`.
4. Replica replicates; the HUD re-renders.
5. `givecoins` Centurion command grants coins through the same mutator.
   `CoinsLeaderstats`, a second `PlayerLoaded` component, injects the wallet
   and mirrors it into the player list.
6. Pure logic (e.g. coin math/validation) lives in `server/features/coins/`
   with a spec file beside it; nothing of the feature reaches the client
   except its HUD and the network event.

A fork deletes the feature by deleting `client/features/coins`,
`server/features/coins`, the `Coins` field of the
schema, the
`requestCoin` network event, and the `givecoins` admin command — and nothing
else.

## Testing

- **Harness:** `@rbxts/jest` (Jest-Lua) running in-engine. `test.project.json`
  builds a test place; `npm test` builds and executes via run-in-roblox.
- **Convention (functional core):** game logic lands as pure functions in the
  layer that owns them (server rules never in `shared/`, ADR 0007),
  `*.spec.ts` beside them. The test place mounts all three trees at their
  game-place paths and runs one Jest project per tree; the game place
  excludes spec files. Services and controllers stay thin shells too simple
  to need their own tests.
- One example spec ships with the coins slice.
- No Lune simulations, no CI in v1.

## Error handling

- Profile session fails to start or conflicts → kick with a clear message.
- Player leaves during `StartSessionAsync` → end the session immediately, no
  entity created.
- Profile load times out or post-load setup throws → end the session and
  kick; a failing migration step never reaches the DataStore because a
  profile that is behind is migrated on a copy.
- No character exists before the profile is loaded: `CharacterAutoLoads` is
  off and `PlayerCharacter` owns respawn (ADR 0006).
- Remote payloads failing Flamework guards or game-rule validation are dropped
  server-side; the client is never trusted.
- Every per-player object owns its connections/instances and releases them in
  `destroy()`; `PlayerService` guarantees `destroy()` runs exactly once per
  entity on leave.

## Documentation deliverables

- **CLAUDE.md** — the invariants: client sends intent; mutators are the only
  write path; services expose behavior, not state; single writer per piece of
  state; per-player objects clean up in `destroy()`.
- **CONTEXT.md** — vocabulary adapted from seed: spine, satellite, fork,
  service, controller, feature, profile, migration, mutator, intent, state.
- **docs/adr/** — seeded with: Flamework over hand-rolled loader; ProfileStore
  + Replica for persistence/replication; React for UI; in-engine Jest;
  template-repo over published packages.
- **README.md** — stack summary, dev-loop instructions, how to fork.

## Out of scope (future satellites)

Monetization (gamepasses/products/receipts), analytics, soft-currency systems
beyond the example, notifications/toasts, daily rewards, leaderboards, codes,
Lune simulation infrastructure, CI.
