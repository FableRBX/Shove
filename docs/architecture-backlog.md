# Architecture backlog

Remaining suggestions from the 2026-09-02 architecture review, after the
loader hardening, the shared-to-server layout move, the rebuild of the player
spine as tag-driven components (ADR 0008), and owner-only replication.
Ordered by how much each item costs to change after the first fork. Delete
items as they land.

**Status when written:** main at `ed961a0` plus this doc, build/lint/19
specs green. The tag-driven flow (sibling injection across
`PlayerPending`/`PlayerLoaded`, deferred tag ordering, the deferred owner
subscribe) has not yet been confirmed in a Studio Play session. Do that
first: `npm run studio`, Play, expect "profile loaded" → character → coin
button works → leaderstats updates → `givecoins` from F2 works.

---

## 1. Intent middleware in the spine

**Why.** `createServer({})` has no middleware. Today "is data loaded" and
throttling are per-handler habits; the coins cooldown is a game rule, not
abuse protection. Flamework runs inbound middleware after its type guards and
before any `connect` handler, per event or per namespace.

**What.**

- Group client→server events under an `intents` namespace in
  `src/shared/network.ts` so middleware applies to the group and new intents
  inherit it without editing a map.
- `requiresLoadedProfile`: drop when `Components.getComponent<PlayerDataNode>`
  is undefined.
- `rateLimit(perSecond)`: per-player, per-event; clear state on
  `PlayerRemoving` or key it on the player's component.
- Register a global bad-request handler that logs guard failures outside
  Studio (Flamework only warns in Studio by default).
- Then `CoinsService` no longer needs its own undefined check.

**Pointers.** `src/server/network.ts`; Flamework docs
`additional-modules/networking/middleware.md`, `namespaces.md`,
`global-handlers.md`. Effort: S–M.

## 3. Schema and write-seam leftovers

- **`Settings` has no feature owner.** Nothing writes it since the
  string-keyed `setSetting` mutator went away; the migrations spec now uses
  it as a spine-owned field for its example steps. Either make a `settings`
  feature with a typed key union and its own component, or delete the field
  and point the spec's steps at `Version` only.
- **Deep writes.** `PlayerDataNode.set` is top-level only; `setEntry` writes
  one entry of a map field, and `insertItem` / `removeItemAt` change one item
  of an array field, each replicating just that change. Deeper paths, if a
  fork needs them, get another typed overload over `Replica.Set([..path])`
  rather than a loosened `set`.
- **Active-session guard, now one line.** The earlier "check `IsActive()` in
  every mutator" idea was rejected as tedious. With a single write seam it is
  one check in `set` (warn and drop when the session is inactive), so the
  objection no longer applies. Still optional: writes after a steal are
  simply lost, not corrupting.
- **Public projection replica.** Profiles are now owner-only. When a fork
  needs nameplate-grade data visible to everyone, add a second token carrying
  a whitelisted projection with `Replicate()`, never the profile itself.

**Pointers.** `src/shared/types/player-data.ts`,
`src/server/services/player/player-data-node.ts`,
`src/server/services/player/migrations.spec.ts`. Effort: S.

## 4. Explicit decisions still defaulted

- **Future-version profiles.** `migrate` leaves a newer-than-`LATEST_VERSION`
  profile untouched, so a rolled-back server reads a newer shape. Options:
  kick with "please update", or warn and continue. Neither live game handles
  it. `src/server/services/player/migrations.ts`.
- **Autosave period.** ProfileStore defaults to 300 s; gsclassic set 60 s
  via `ProfileStore.SetConstant("AUTO_SAVE_PERIOD", 60)` to shrink the
  crash-loss window. Pick one in `PlayerService.onStart`.
- **Admin ids.** `ADMIN_IDS` is hardcoded in `src/server/commands/admin.ts`;
  move to a config module a fork edits without touching command code.
- **Error sink.** Everything warns. A one-function `report(message, context)`
  seam (default: warn) lets a fork plug in AnalyticsService the way gsclassic
  does, without editing call sites. Wire ProfileStore's `OnError`/`OnOverwrite`
  and the load-failure paths through it.

Effort: S each.

## 5. Satellite requirements learned from the live games

Not spine work, but record them so the first satellites do not relearn them.

- **Receipts.** Grant a developer product only after the purchase id reaches
  `Profile.LastSavedData` under an active session, with a bounded re-`Save()`
  poll (gsclassic closed a live duplicate-grant exploit this way; ProfileStore
  docs `devproducts` page has the reference implementation).
- **Teleports.** End the session before `TeleportAsync`, with a cooldown and a
  bounded retry, or the destination server stalls on the session lock.
- **Loading screen.** Hold until the character exists, set `ResetOnSpawn`
  false on the GUI so it survives the spawn it waits for, and add a hard
  timeout (gsclassic: 30 s). With spawn gated on data (ADR 0006) the
  character is the only signal the client needs. A data-only gate for the
  local player is `PlayerDataStore.onReady` behind a hook; the client bridge
  left it out because no feature waits on data alone.
- **Client components on `PlayerLoaded`.** Both lifecycle tags replicate, so
  a client can mirror the server's component model: a component bound to
  `PlayerLoaded` for every player (nameplates) and a predicate-scoped one for
  the local player. Left out of the client bridge; add it with the first
  feature that needs per-player client state.

## 6. Testing gap

Only pure functions are tested. The spine's behaviour now lives in
components whose inputs are Flamework, tags, and a `Player` instance, none of
which the in-engine Jest place provides. Keep extracting decisions into pure
policy modules (the pattern in `session-policy.ts`). If a component ever
needs a test, the seam is a Folder-typed variant of the component, not a fake
`Player`. Accept the gap otherwise; the Play checklist at the top is the
integration test.

## 7. Repo housekeeping before forking

- The GitHub repo is private and not flagged as a template. GitHub will not
  fork a private repo into the same account: either mark it a template
  (squashed history, so later spine merges need `--allow-unrelated-histories`)
  or clone and repoint the remote (keeps history so `git merge` from the
  template works, per ADR 0005).
- Delete the stale `spine` branch locally and on origin.

---

**Decided and done, for orientation:** nil-profile handling, cancel/timeout,
fault-isolated setup, gated session-end kick, mock store in Studio, spawn
after profile (ADR 0006), ProfileStore error logging, server-only logic out
of `src/shared/` (ADR 0007), per-player state as tagged components with a
single write seam (ADR 0008), owner-only profile replication deferred until
the client's Replica is ready, the client data bridge (path subscriptions,
field hooks through `PlayerDataProvider`, `UiController.mount`), Node 24 pin
with Prettier in `npm run lint`, `npm run studio`.
