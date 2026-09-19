# 0008 — Player lifecycle as tagged components

**Context.** The first spine kept per-player state in `PlayerService`: a map
of entities, `playerReady`/`playerRemoving` signals, getters, and a data node
that every feature extended with its own mutators and signals. Features
either bound components to a tag or kept `Map<Player, T>` in services, and a
service that started after a profile had loaded could miss that player.
Flamework constructs components in response to tags and resolves sibling
components by injection, so per-player state already has a native home that
the service pattern was reimplementing.

**Decision.** Two CollectionService tags carry the lifecycle. `PlayerService`
owns only the store and adds `PlayerPending` on join. `PlayerProfile` (bound
to `PlayerPending`) owns the session: it loads in a spawned thread and on
success adds `PlayerLoaded`. `PlayerDataNode` (the Replica and the single
typed `set` seam), `PlayerCharacter`, and every feature's per-player
component bind to `PlayerLoaded` and inject what they need. On leave the
service removes Loaded, then Pending, so dependents are destroyed before the
session ends. Intent handlers resolve a `PlayerLoaded` component through
`Components`; undefined means the data is not ready and the intent is
dropped.

**Consequences.** No hand-off of the profile, no ready signal, no boot sweep
in consumers, no per-player maps in services. Features stop editing the data
node: mutators and change signals live on the feature's own component, so
deleting a feature no longer touches the spine. Flamework calls `onStart`
synchronously inside component setup, so anything that yields there runs in
its own thread and re-checks `destroyed` after the yield. Both tags
replicate, so clients can bind components to them as well.
