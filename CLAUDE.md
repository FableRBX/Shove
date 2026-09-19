# anvil

A fork-per-game Roblox template built with roblox-ts and Flamework. Every game
starts as a fork of this repo, so the spine is permanent: a mistake here cannot
be un-shipped from games already forked. Invariants outrank features.

## Invariants

- **The client sends intent; the server decides.** Client→server events are
  named as requested actions (`requestCoin`), never resulting states. Handlers
  validate game rules and silently drop invalid intents.
- **Profile writes go only through a feature's per-player component**
  (`CoinsWallet.addCoins`): operation-shaped mutators that validate, call the
  typed write seam on `PlayerDataNode` (`set`, `setEntry`, `insertItem`,
  `removeItemAt`), and announce the change. Nothing else calls the seam. All
  other access is `getData(): Readonly<PlayerData>`.
- **Services expose behavior and signals, not raw state.** One writer per
  piece of state.
- **Per-player state is a Flamework component on the Player instance**, bound
  to `PlayerLoaded`, that releases what it owns in `destroy()`. Flamework
  destroys it exactly once when the tag comes off on leave. No
  `Map<Player, T>` in services.
- **Game logic is a functional core**: pure functions with `*.spec.ts` beside
  them, living in the layer that owns them; services and controllers stay thin
  shells.
- **`src/shared/` is the client-visible surface and nothing more**: types, the
  network contract, replica tokens, constants the client renders with. Clients
  can decompile it, so server rules, defaults, migrations, and utilities live
  in `src/server/` (ADR 0007).

## Layout

`src/{client,server,shared}` — layer-first at the Rojo boundary, feature-first
within. A **feature** is a deletable unit of gameplay: deleting it means
deleting its `features/<name>/` folders plus its schema field and network
events — and nothing else. The `coins` feature is the living example
of every seam; read it before adding a feature.

## Stack

Flamework (services/controllers/components, DI, typed networking), ProfileStore
(persistence, session locking), loleris-replica (server→client replication),
@rbxts/react (UI, portal-mounted from controllers), Centurion (F2 dev console),
@rbxts/jest (in-engine tests). Decisions live in `docs/adr/`.

## Commands

- `npm run build` / `npm run watch` — compile TS → Luau
- `npm run assemble` — compile + build `anvil.rbxl`
- `npm run studio` — assemble, then open `anvil.rbxl` in a new Studio
  instance (`npm run open` opens without rebuilding). Every run opens a fresh
  window; an already-open Studio shows the build it loaded, not the rebuild.
- `npm test` — compile, build test place, run Jest in-engine. Specs are
  discovered in all three layers; spec files and the Jest config are excluded
  from the game place. (One-time machine setup: `npm run test:setup`, which
  writes Studio's `FFlagEnableLoadModule`.)
- `npm run lint` — eslint

After switching branches or moving files, delete `out/` before building or
testing: rbxtsc's incremental cache (`out/tsconfig.tsbuildinfo`) can consider
restored files up-to-date and skip re-emitting them, and stale emits from old
paths stay behind — specs then hang forever on `WaitForChild` for modules that
never got compiled, or run twice.

## Data

Schema in `src/shared/types/player-data.ts` (interface and replica token
only). Defaults and migrations are server-only, in
`src/server/services/player/`. Additive changes: extend the interface and
`DEFAULT_PLAYER_DATA` (ProfileStore `Reconcile` fills old profiles). Shape
changes: bump `LATEST_VERSION` and add a step in `migrations.ts`; a profile
that is behind is migrated on a copy, so a failing step never reaches the
DataStore.

## Player lifecycle

Per-player state is components on the Player instance, driven by two tags
(ADR 0008). `PlayerService` owns the ProfileStore store (the mock store in
Studio, so nothing persists across Play) and adds `PlayerPending` on join.
`PlayerProfile` (bound to `PlayerPending`) starts the session, reconciles,
migrates if behind, then adds `PlayerLoaded`. That constructs `PlayerDataNode`
(Replica plus the `set` seam), `PlayerCharacter` (spawn, respawn and walk
speed, which it re-applies to every body; `CharacterAutoLoads` is off, ADR
0006), and every feature component bound to `PlayerLoaded`. A load that
fails or times out kicks with a rejoin message; default data is never
substituted. On leave the tags come off, Loaded first, so feature components
are destroyed before the session ends. To ask whether a player's data is
ready, ask `Components` for a `PlayerLoaded` component; undefined means not
yet. Session decisions are pure functions in
`src/server/services/player/session-policy.ts`.

## Client data and UI

The client keeps Replica's change path. `PlayerDataController` implements
`PlayerDataStore` (`getData`, `subscribe(path, listener)`, `onReady`): one
`OnChange` connection dispatches each write to the subscribers whose path
overlaps it (either is a prefix of the other), so a feature re-renders for
the fields it reads and nothing else. Components read profile data only
through `usePlayerField(key)`, `usePlayerEntry(key, id)` and
`usePlayerSelector(fields, selector, equals?)` in `src/client/ui/hooks/`,
which take the store from `PlayerDataProvider` via React context; never
call `Dependency<>()` inside a hook. A selector returns a primitive or
builds a new value, never a sub-table of the mirror, which Replica mutates
in place. Per-player state that is not in the profile (a cap, a cooldown)
travels as an attribute the server sets on the Player and the client reads
with `usePlayerAttribute(name)`. Every React root is created by
`UiController.mount(name, element, options?)`, which owns the container,
root, portal, ScreenGui and provider; a feature controller injects
`UiController` and mounts its own UI in one call, so deleting the feature
still deletes its interface. Feature-specific contexts wrap inside the
element the feature passes in.
