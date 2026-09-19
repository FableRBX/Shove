# 0005 — Template repo over published packages

**Context.** The spine could ship as versioned npm packages that forks depend
on, or as ordinary source files in a template repo.

**Decision.** Template repo. Every game forks it; spine code is ordinary
editable source. Improvements flow forward by forking fresh, or into a live
game via `git merge` from the template remote.

**Consequences.** No publishing/versioning infrastructure to run; forks may
freely patch their spine. The cost: fixes do not propagate automatically —
merging upstream is a deliberate per-game act.
