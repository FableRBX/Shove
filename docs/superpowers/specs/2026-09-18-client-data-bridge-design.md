# Client data bridge: path subscriptions and field hooks

**Date:** 2026-09-18
**Status:** Implemented (2026-09-18); pure specs green; Studio Play checklist
in section 7 not yet run
**Builds on:** ADR 0002 (ProfileStore and Replica), ADR 0003 (React),
architecture backlog item 2
**Origin:** Ported from Kaiju's spec of the same name (2026-09-16), which
was implemented and Play-verified there. Names adapted (`[anvil]`,
`AnvilApp`); the design is unchanged so every fork of this template gets
the same bridge.

## Purpose

Today `PlayerDataController` listens to every Replica change, throws the
path away, and re-publishes a shallow copy of the whole document; the one
hook, `usePlayerData()`, hands that document to every subscriber, so a
coins label re-renders when any other field is written. The server already
writes one field, one entry, or one array item at a time, and Replica
ships exactly that path. This step keeps the path on the client: a
feature subscribes to the fields it renders and nothing else. It also
gives every feature one way to mount UI, so the data store reaches
components through React context instead of `Dependency<>()` inside
hooks.

Out of scope: batching renders across fields, client components bound to
`PlayerLoaded`, a loading screen, and any change to the server node or the
network contract.

## Decisions

- **Subscriptions are by path, built on `OnChange`.** Replica's `OnSet`
  matches an exact path only and never fires for inserts or removes, so it
  cannot express "anything under `Settings`". `OnChange` sees every write
  with its action and path. One connection dispatches to subscribers with
  a tested overlap rule: a change fires a subscriber when either path is a
  prefix of the other. An entry write reaches the field's subscribers and
  that entry's; a wholesale field write reaches every entry beneath it.
- **Listeners get the change, not a snapshot.** Action, path, value and
  detail, with the mirror already updated, so a controller can react to
  "entry added" or "item removed" without diffing. React hooks read the
  current value by path after each change.
- **Tables handed to React are shallow-cloned.** Replica mutates the mirror
  in place, so `Data.Settings` is the same table before and after an
  entry write and reference equality cannot see the change. Cloning the
  one field a hook returns is cheap; cloning the document was not.
- **Selectors are explicit about their fields.** `usePlayerSelector`
  takes the field list it depends on, subscribes to those, and re-renders
  only when the result differs. Because sub-tables of the mirror keep
  their reference, the documented rule is that a selector returns a
  primitive or builds a new value.
- **The store reaches hooks through context, and every root is mounted
  by one spine controller.** `UiController.mount` owns the Folder, root,
  portal and ScreenGui that feature controllers copy today, and wraps the
  tree in the provider. Hooks stop calling `Dependency<>()` in render and
  can be exercised with a fake store. Feature-specific contexts wrap
  inside the element the feature passes in, so the spine never learns
  about features.
- **`AppController` folds into `UiController`.** Two spine mount points
  would be one too many; the shell is mounted through the same call.
- **The root container is an unparented Folder, and `UiController` holds
  every live root.** `PlayerGui` destroys everything but
  `ResetOnSpawn`-false GUIs on respawn, so a container parented there dies
  on the first reset. Nothing renders into the container (everything goes
  through the portal), so it needs no parent, exactly as the react-roblox
  README shows. A `Set<Root>` on the controller keeps the fiber tree
  strongly reachable; `unmount` drops the entry.
- **Dispatch order is subscription order, held in arrays.** Luau `pairs`
  over a `Set` or `Map` does not preserve insertion order, so the buckets
  are arrays with `indexOf` removal. Dispatch iterates a copy so a listener
  that unsubscribes mid-dispatch cannot skip its neighbour.
- **Not Charm, not one Replica per feature.** A second state library
  beside Replica only to slice it, or splitting the profile across
  replicas, buys nothing the path already carries (ADR 0002).
- **Assumptions stated:** a hook that reads two fields changed in one
  network step renders twice, which is invisible at this scale;
  `useDeferState` from pretty-react-hooks is the one-line fix if it ever
  shows. A table-valued field hook renders once more at mount than a
  primitive one, because `onReady` fires synchronously in the effect and
  hands it a fresh clone; React bails out for an identical primitive.

## 1. Shared types

`src/shared/types/player-data.ts` gains the two field-kind helpers the
server node defines privately today, so both sides share one definition:

```ts
/** Fields of PlayerData that are arrays, eligible for per-item inserts and removes. */
export type ArrayField = { [K in keyof PlayerData]: PlayerData[K] extends unknown[] ? K : never }[keyof PlayerData];
/** Fields of PlayerData that are maps (string-keyed tables), eligible for per-entry writes. */
export type MapField = { [K in keyof PlayerData]: PlayerData[K] extends unknown[] ? never : PlayerData[K] extends { [id: string]: unknown } ? K : never }[keyof PlayerData];
```

`PlayerDataNode` imports them. Nothing else on the server changes. In the
template schema `MapField` is `"Settings"` and `ArrayField` is `never`
until a fork adds an array field.

## 2. The store

`src/client/controllers/player-data-store.ts` (types only):

```ts
export type DataPath = ReadonlyArray<string | number>;
export type DataAction = "Set" | "SetValues" | "TableInsert" | "TableRemove";
export interface DataChange {
	action: DataAction;
	path: DataPath;
	/** Set: the new value (undefined removes). SetValues: the values table. TableInsert: the inserted item. TableRemove: the removed item. */
	value: unknown;
	/** Set: the old value. TableInsert and TableRemove: Replica's one-based index. */
	detail?: unknown;
}
export interface PlayerDataStore {
	/** The live mirror, or undefined until it arrives. Never mutate it. */
	getData(): Readonly<PlayerData> | undefined;
	/** Fires for every change whose path overlaps `path`, after the mirror has been updated. Returns unsubscribe. */
	subscribe(path: DataPath, listener: (change: DataChange) => void): () => void;
	/** Fires once with the mirror: now if it has arrived, else when it does. Returns unsubscribe. */
	onReady(listener: (data: Readonly<PlayerData>) => void): () => void;
}
```

`src/client/controllers/path-subscriptions.ts` (pure, spec):

```ts
/** True when either path is a prefix of the other. The empty path is a prefix of everything. */
export function pathsOverlap(a: DataPath, b: DataPath): boolean;

/** Subscribers bucketed by first key; root subscribers (empty path) in their own bucket. */
export class PathSubscriptions {
	subscribe(path: DataPath, listener: (change: DataChange) => void): () => void;
	/** Root bucket first, then the change's first-key bucket, each filtered by pathsOverlap. A listener that errors is reported with warn and does not stop the others. */
	dispatch(change: DataChange): void;
	count(): number;
}
```

`src/client/controllers/data-path.ts` (pure, spec): `getAt(data:
unknown, path: DataPath): unknown`, undefined when any step is missing or
not a table; a numeric key is used raw as Replica's Luau one-based index.
`snapshot(value)` is `table.clone` for a table and identity otherwise.

`PlayerDataController` implements `PlayerDataStore`. `OnNew` for the
player-data token keeps the owner guard, stores the replica, connects
`OnChange` to `subscriptions.dispatch` with the four arguments mapped into
a `DataChange`, and fires ready listeners once. `dataChanged` and the
snapshot copy go away.

## 3. Context and hooks

`src/client/ui/player-data-context.tsx`:

```tsx
export const PlayerDataContext: React.Context<PlayerDataStore | undefined>;
export function PlayerDataProvider(props: { store: PlayerDataStore; children?: React.ReactNode }): React.Element;
/** The store from context. Throws "[anvil] no PlayerDataProvider: mount UI through UiController" outside one. */
export function usePlayerDataStore(): PlayerDataStore;
```

`src/client/ui/hooks/`, replacing `use-player-data.ts`:

```ts
// use-player-field.ts
/** The field, re-rendering only when it or anything beneath it changes. Tables come back shallow-cloned. Undefined until the mirror arrives. */
export function usePlayerField<K extends keyof PlayerData>(key: K): Readonly<PlayerData[K]> | undefined;

// use-player-entry.ts
/** One entry of a map field; undefined until the mirror arrives or when the entry is absent. */
export function usePlayerEntry<K extends MapField>(key: K, id: string): Readonly<PlayerData[K][string]> | undefined;

// use-player-selector.ts
/** Recomputes on changes to `fields` only; re-renders when `equals` (default ===) says the result changed. Return a primitive or a new value, never a sub-table of the mirror. */
export function usePlayerSelector<T>(fields: ReadonlyArray<keyof PlayerData>, selector: (data: Readonly<PlayerData>) => T, equals?: (a: T, b: T) => boolean): T | undefined;
```

Each hook takes the store from `usePlayerDataStore`, seeds state from
`getData()` when present, and in one effect keyed on the store and its
arguments registers `onReady` and `subscribe` for its path or fields,
unsubscribing on cleanup. A field or entry hook sets state to
`snapshot(getAt(data, path))`. The selector hook keys its effect on
`[store, fields.join(",")]` and reads `selector` and `equals` through
`useLatest` refs, because keying on an inline array or closure would
re-subscribe every render, fire `onReady` synchronously, set a fresh
table, and loop forever. It sets state through an updater that keeps the
previous value when `equals` holds.

## 4. Mounting

`src/client/controllers/ui-controller.tsx` replaces `app-controller.tsx`:

```tsx
export interface MountOptions {
	ignoreGuiInset?: boolean;
	displayOrder?: number;
}

@Controller({})
export class UiController implements OnStart {
	constructor(private readonly data: PlayerDataController) {}

	/** Mounts the App shell in the AnvilApp ScreenGui. */
	onStart(): void;

	/**
	 * Mounts a feature's UI: a root on an unparented Folder, and a portal to
	 * a ScreenGui named `name` in PlayerGui (ResetOnSpawn off, ZIndexBehavior
	 * Sibling) wrapped in PlayerDataProvider. Returns unmount.
	 */
	public mount(name: string, element: React.Element, options?: MountOptions): () => void;
}
```

Feature controllers inject it and shrink to one line:

```tsx
@Controller({})
export class CoinsHudController implements OnStart {
	constructor(private readonly ui: UiController) {}
	onStart(): void {
		this.ui.mount("CoinsHud", <CoinsHud />);
	}
}
```

`CoinsHud` reads `usePlayerField("Coins")`. `App` loses its own
`screengui` and returns an empty fragment; the shell's ScreenGui comes
from `UiController.mount("AnvilApp", <App />, { ignoreGuiInset: true })`.

## 5. Documentation

- ADR 0002, dated addendum: the client keeps the change path; no document
  re-publish.
- ADR 0003, dated addendum: field hooks through `PlayerDataProvider`;
  every root mounted by `UiController.mount`; the container Folder stays
  unparented; feature contexts wrap inside the passed element; never
  `Dependency<>()` inside a hook.
- `docs/architecture-backlog.md`: item 2 deleted, its two optional
  bullets (client components on `PlayerLoaded`, a loading gate) folded
  into item 5.
- `CLAUDE.md`: a short "Client data and UI" section so every fork reads
  the rules without opening the ADRs.

## 6. Errors

| Condition                                  | Behaviour                                                                |
| ------------------------------------------ | ------------------------------------------------------------------------ |
| Hook rendered before the mirror arrives    | returns undefined; fills in on ready                                     |
| Hook rendered outside a provider           | throws with the mount instruction                                        |
| Subscribe before the replica exists        | registered; fires as changes flow                                        |
| Listener throws                            | reported with `warn`; the rest still run                                 |
| Selector returns a sub-table of the mirror | never re-renders after the first value; the rule in section 3 is the fix |
| Entry removed                              | entry hook yields undefined                                              |
| Player leaves                              | replica destroyed by Replica; nothing to release                         |

## 7. Testing

Pure specs beside their modules: `path-subscriptions` (`pathsOverlap`:
equal, prefix either way, sibling, empty; `dispatch`: root and bucket
order, unrelated bucket untouched, entry filtering within a bucket,
wholesale field write reaching entries, empty-path change reaching every
bucket, unsubscribe, a throwing listener does not block the next) and
`data-path` (`getAt`: nested hit, empty path, missing step, non-table
step, numeric key as a one-based index; `snapshot`: primitives pass
through, tables clone one level). Hooks and `UiController` are not unit
tested (backlog item 6). Studio Play checklist:

1. Coins HUD shows the balance; Get Coin increments it; `givecoins` from
   the F2 console too. The console shows `player data replica received`
   once.
2. With a temporary `print` as the first line of `CoinsHud`'s render
   (removed after): one or two renders at mount, then exactly one per
   coin write. The template has no second feature writing another field,
   so field isolation is pinned by the `path-subscriptions` spec rather
   than observed here; a fork's first extra feature can confirm it.
3. Reset the character: the HUD survives the respawn and still updates
   afterwards. `PlayerGui` holds one `CoinsHud` and one `AnvilApp`
   ScreenGui and no Folders.
4. F2 opens the dev console over the HUD.
