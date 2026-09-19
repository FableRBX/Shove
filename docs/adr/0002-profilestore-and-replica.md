# 0002 — ProfileStore + Replica for persistence and replication

**Context.** The data pipeline needs session-locked persistence and
server→client mirroring. The adjacent `Hatch` project proved
`@rbxts/profile-store` + `@rbxts/loleris-replica` under roblox-ts. The
alternative modern stack (Charm atoms + charm-sync + Lapis) is more idiomatic
TS but unproven in this portfolio.

**Decision.** ProfileStore owns the profile document (`PlayerProfile` holds
the session); `PlayerDataNode` creates a Replica over `profile.Data` and
exposes one typed `set`, which feature mutators call so every change
replicates. Clients read via `ReplicaClient.OnNew(token)`.

**Consequences.** Mutable document + path-based writes (not immutable
snapshots); the client controller re-publishes a fresh object per change so
React re-renders. The node subscribes only the owning player, so a profile
is private by default; state every client should see gets its own Replica
with `Replicate()`.

**Client bridge (2026-09-18).** The client keeps the change path.
`PlayerDataController` implements `PlayerDataStore`: one `OnChange`
connection dispatches each write by path to subscribers (a change fires a
subscriber when either path is a prefix of the other), so a feature
re-renders for the fields it reads and nothing else. The controller no longer
re-publishes a document per change; Replica mutates the mirror in place, and
a hook shallow-clones only the field it returns. Ported from Kaiju, where it
was Play-verified on 2026-09-16.
