# 0006 — Characters spawn only after the profile loads

**Context.** With Roblox's default `CharacterAutoLoads`, the character spawns
at join while `StartSessionAsync` is still yielding: seconds normally, ~40s on
a session-steal rejoin, minutes in a DataStore outage. Every consumer of
`CharacterAdded` then has to handle a character that predates the data, and
the placeholder-character bug class follows. Of the adjacent live games,
TamingSimulator absorbs the race by re-processing an existing character;
gsclassic gates spawn on data and documents the loading-screen and
spawn-placement regressions that motivated it.

**Decision.** `CharacterAutoLoads` is declared off in `default.project.json`
and re-asserted in `PlayerService`. `PlayerCharacter` is a component bound to
`PlayerLoaded` (ADR 0008), so it cannot exist before the profile; it defers
the first spawn one step so sibling components construct before a body
exists. Because the engine no longer auto-respawns, `PlayerCharacter` owns
respawn: `Humanoid.Died` → `Players.RespawnTime` → `spawn()`, guarded against
the player having left or already being alive.

**Consequences.** Nothing gameplay-visible exists until data is ready; the
"server decides" invariant now covers spawning. A slow load leaves the player
characterless until it resolves or `PROFILE_LOAD_TIMEOUT` kicks them; a fork
that wants a placeholder body or a loading screen adds it as a satellite.
Forks that re-enable auto-load keep working: the component processes an
existing character on start. Consumers use both paths, `getCharacter()` for a
body that already exists and `characterAdded` for the next one.
