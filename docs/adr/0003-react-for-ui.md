# 0003 — React for UI

**Context.** The spine ships a UI mount. The portfolio's Luau work already
uses React-Lua, and `@rbxts/react` is the maintained roblox-ts binding.

**Decision.** `@rbxts/react` + `@rbxts/react-roblox`. Controllers mount roots
into an owned Folder and portal into PlayerGui (roots take ownership of their
container). Features mount their own ScreenGuis so deleting a feature deletes
its UI. Data reaches components through the `usePlayerData` hook.

**Consequences.** JSX/TSX with `React.createElement` factories in tsconfig;
declarative UI testable by inspection; a second render tree (Roblox instances)
owned entirely by React — never mutate React-owned instances imperatively.

**Hooks and motion (2026-09-15).** `@rbxts/pretty-react-hooks` is the
sanctioned source of utility hooks (motion, springs, viewport, key press,
tagged instances, intervals, `useLatest`); do not hand-roll these. It brings
`@rbxts/ripple` for springs and tweens. The direct `@rbxts/ripple` pin
follows the line the hooks package depends on, so the place holds one copy.
Both declare any `@rbxts/react` as a peer, so they never duplicate React.

**Field hooks and one mount point (2026-09-18).** `usePlayerData` is gone.
Components read `usePlayerField`, `usePlayerEntry` and `usePlayerSelector`
from `src/client/ui/hooks/`, which take the store from `PlayerDataProvider`
through React context. Never call `Dependency<>()` inside a hook: the store
comes from context, so a component can be exercised with a fake store. A
selector returns a primitive or builds a new value, never a sub-table of the
mirror, because Replica mutates those in place. Every root is mounted by
`UiController.mount(name, element, options?)`, which owns the container,
root, portal, ScreenGui and provider that feature controllers used to copy;
`AppController` folded into it. The container Folder stays unparented, as
the react-roblox README shows: nothing renders into it, and PlayerGui
destroys everything but `ResetOnSpawn`-false GUIs on respawn. The controller
holds every live root so an unparented container is never left to the
garbage collector. A feature-specific context wraps inside the element the
feature passes in, so the spine never learns about features. Ported from
Kaiju, where it was Play-verified on 2026-09-16.
