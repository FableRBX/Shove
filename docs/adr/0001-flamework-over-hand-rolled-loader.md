# 0001 — Flamework over a hand-rolled loader

**Context.** The Luau predecessor (`seed`) rejected game frameworks and DI in
favor of a ~100-line loader, valuing transparency over convenience. roblox-ts
changes the calculus: Flamework is the ecosystem's dominant backbone, its DI is
compile-time-generated (no runtime registry or string lookup), and its
networking macros produce runtime type guards for free.

**Decision.** Use Flamework core/components/networking as the spine's
backbone: `@Service`/`@Controller` lifecycle classes, constructor injection,
typed `GlobalEvents`.

**Consequences.** Every fork depends on Flamework and its transformer; the
`flamework.build` id file must be committed. In exchange: no loader to
maintain, DI without magic strings, and validated remotes without hand-written
guards.
