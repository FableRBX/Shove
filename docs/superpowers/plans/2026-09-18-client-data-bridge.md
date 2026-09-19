# Client Data Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The client keeps Replica's change path: a feature subscribes to the fields it renders and nothing else, hooks take the data store from React context, and every UI root is mounted by one spine controller.

**Architecture:** `PlayerDataController` implements a small `PlayerDataStore` interface over the one Replica: it connects `OnChange` once and hands each change to a pure `PathSubscriptions` dispatcher that fires a subscriber when either path is a prefix of the other. Three hooks (`usePlayerField`, `usePlayerEntry`, `usePlayerSelector`) read the store from `PlayerDataContext`, seed from the mirror, and re-read by path on each overlapping change, shallow-cloning any table they return so React sees a new reference. `UiController.mount(name, element, options?)` owns the Folder, root, portal, ScreenGui and provider that feature controllers copy today; `AppController` folds into it.

**Tech Stack:** roblox-ts, Flamework controllers and DI, `@rbxts/loleris-replica` (client `OnChange`), `@rbxts/react` + `@rbxts/react-roblox` (context, portals), `@rbxts/pretty-react-hooks` (`useLatest`), `@rbxts/jest` in-engine specs.

**Spec:** `docs/superpowers/specs/2026-09-18-client-data-bridge-design.md`

**Origin:** A port of Kaiju's plan of the same name (2026-09-16). The code is the final Kaiju source with the `[anvil]` log prefix and the `AnvilApp` shell name; every file is in the tree, so this plan lists files and checks rather than embedding code.

## Global Constraints

- **Nothing on the server changes** except `PlayerDataNode` importing the two field-kind types from `src/shared/types/player-data.ts` instead of defining them. No network contract change.
- **`src/shared/` gains only `ArrayField` and `MapField`** (types). Everything else lives in `src/client/`.
- **Never `Dependency<>()` inside a hook.** Hooks take the store from `usePlayerDataStore()` (React context), which `UiController.mount` supplies.
- **Subscriptions are by path, built on Replica's `OnChange`.** A change fires a subscriber when either path is a prefix of the other; the empty path is a prefix of everything.
- **Dispatch order:** root subscribers first, then the change's first-key bucket; within each, subscription order, held in arrays.
- **Tables handed to React are shallow-cloned**; a selector returns a primitive or builds a new value.
- **Error strings:** a hook outside a provider throws `[anvil] no PlayerDataProvider: mount UI through UiController`; a throwing listener is reported with `warn` and the rest still run.
- **Hook effect keys:** field and entry hooks key on `[store, key]` / `[store, key, id]`; the selector keys on `[store, fields.join(",")]` and reads `selector` and `equals` through `useLatest` refs, or an inline array or closure loops forever.
- **Reserved identifiers:** `select` and `next` are Luau globals that rbxtsc refuses; the selector parameter is `selector` and its result `selected`.
- **Commands.** `npm run build`, `npm run lint`, `npm test` (in the Bash tool prefix `export PATH="$HOME/.rokit/bin:$PATH" &&` so `run-in-roblox` resolves). Baseline before this plan: 5 suites, 19 tests, 2 projects (no client specs yet).
- **After deleting files, `rm -rf out` before building** (Task 5 deletes two). `flamework.build` is tracked and changes in Task 5.

---

## File structure

| File                                                   | Responsibility                                                                        |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------- |
| `src/shared/types/player-data.ts`                      | + `ArrayField`, `MapField` (types both sides share)                                   |
| `src/server/services/player/player-data-node.ts`       | imports them; its private copies go                                                   |
| `src/client/controllers/player-data-store.ts`          | types only: `DataPath`, `DataAction`, `DataChange`, `PlayerDataStore`                 |
| `src/client/controllers/path-subscriptions.ts` (+spec) | `pathsOverlap`, `PathSubscriptions` (subscribe / dispatch / count)                    |
| `src/client/controllers/data-path.ts` (+spec)          | `getAt`, `snapshot`: read the mirror by path, clone what React gets                   |
| `src/client/controllers/player-data-controller.ts`     | implements `PlayerDataStore` over the replica; `dataChanged` and the document copy go |
| `src/client/ui/player-data-context.tsx`                | `PlayerDataContext`, `PlayerDataProvider`, `usePlayerDataStore`                       |
| `src/client/ui/hooks/use-player-field.ts`              | `usePlayerField(key)`                                                                 |
| `src/client/ui/hooks/use-player-entry.ts`              | `usePlayerEntry(key, id)`                                                             |
| `src/client/ui/hooks/use-player-selector.ts`           | `usePlayerSelector(fields, selector, equals?)`                                        |
| `src/client/ui/hooks/use-player-data.ts`               | **deleted**                                                                           |
| `src/client/controllers/ui-controller.tsx`             | `UiController.mount`; mounts `App`; **replaces `app-controller.tsx` (deleted)**       |
| `src/client/ui/app.tsx`                                | shell returns an empty fragment; no ScreenGui                                         |
| `src/client/features/coins/coins-hud-controller.tsx`   | one line: `this.ui.mount("CoinsHud", <CoinsHud />)`                                   |
| `src/client/features/coins/coins-hud.tsx`              | `usePlayerField("Coins")`                                                             |
| `docs/adr/0002-profilestore-and-replica.md`            | dated addendum: the client keeps the change path                                      |
| `docs/adr/0003-react-for-ui.md`                        | dated addenda: hooks package; field hooks through the provider; one mount point       |
| `docs/architecture-backlog.md`                         | item 2 deleted; its optional bullets folded into item 5                               |
| `CLAUDE.md`                                            | "Client data and UI" section                                                          |

---

### Task 1: Share `ArrayField` and `MapField`

- [x] Append the two aliases to `src/shared/types/player-data.ts`.
- [x] `PlayerDataNode` imports them; delete its private copies.
- [x] `npm run build` passes.

### Task 2: Store types and `PathSubscriptions` (spec first)

- [x] Write `player-data-store.ts` (types only).
- [x] Write `path-subscriptions.spec.ts` (12 cases: overlap rule; dispatch order; unrelated bucket; entry filtering; wholesale field write; empty-path change; unsubscribe; throwing listener).
- [x] Build fails with `Cannot find module './path-subscriptions'` (red).
- [x] Write `path-subscriptions.ts`; build passes; specs green.

### Task 3: `getAt` and `snapshot` (spec first)

- [x] Write `data-path.spec.ts` (7 cases, including the numeric key as a Luau one-based index).
- [x] Build fails with `Cannot find module './data-path'` (red).
- [x] Write `data-path.ts`; build passes; specs green. `npm test`: 7 suites, 38 tests, 3 projects.

### Task 4: `PlayerDataProvider` and the three hooks

- [x] Write `player-data-context.tsx`.
- [x] Write `use-player-field.ts`, `use-player-entry.ts`, `use-player-selector.ts`.
- [x] Not unit tested (backlog item 6); covered by the Play checklist in Task 7.

### Task 5: The switch-over

- [x] Rewrite `player-data-controller.ts` to implement `PlayerDataStore`.
- [x] Write `ui-controller.tsx`; `app.tsx` returns an empty fragment.
- [x] `coins-hud-controller.tsx` injects `UiController` and mounts in one line; `coins-hud.tsx` reads `usePlayerField("Coins")`.
- [x] Delete `app-controller.tsx` and `use-player-data.ts`; `grep -rnE "usePlayerData\b|dataChanged|AppController" src` returns nothing.
- [x] `rm -rf out`, `npm run build` (regenerates `flamework.build`: `AppController` out, `UiController` in), `npm run lint`, `npm test` all pass.

### Task 6: Documentation

- [x] ADR 0002 addendum; ADR 0003 addenda; backlog item 2 removed and folded into item 5; CLAUDE.md section; this spec and plan.

### Task 7: Studio Play checklist and closing the spec

Add a temporary `print("[anvil] CoinsHud render")` as the first line of `CoinsHud`, `npm run studio`, Play, then:

- [ ] Coins HUD shows `Coins: 0`; Get Coin increments it; `givecoins <you> 50` from F2 adds 50; the console shows `player data replica received` once.
- [ ] Render count: one or two at mount, then exactly one per coin write.
- [ ] Reset the character: the HUD survives the respawn and still updates; `PlayerGui` holds one `CoinsHud` and one `AnvilApp` ScreenGui and no Folders.
- [ ] F2 opens the dev console over the HUD.
- [ ] Remove the print; mark the spec's status "Play checklist passed".
