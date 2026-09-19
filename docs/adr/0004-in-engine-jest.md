# 0004 — In-engine Jest for tests

**Context.** Game logic lands as pure functions beside the layer that owns
them (functional core). Those need a runner. Jest Lua runs the real compiled
Luau inside the real engine — no semantic drift between test and production
runtimes, unlike running the TS under Node.

**Decision.** `@rbxts/jest` specs (`*.spec.ts`) colocated with the logic;
`test.project.json` builds a place mounting the shared, server, and client
trees at their game-place paths (runtime scripts excluded, no Flamework
ignition), with Jest `roots` spanning all three; `run-in-roblox` executes
`scripts/run-tests.luau`. The game place excludes spec files.

**Consequences.** Tests need Studio installed and the one-time
`FFlagEnableLoadModule` setup (`npm run test:setup`); runs cost seconds, not
milliseconds — so services stay thin and logic stays pure to keep the tested
surface wide and the suite small. Jest reloads modules per suite, which trips
RuntimeLib's duplicate-runtime guard; `scripts/jest-setup.luau` (wired via
`setupFiles`) clears the stale `_G` stamps between suites.
