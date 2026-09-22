# In-engine checks for the giant prefabs

Run against a built preview place with `run-in-roblox` (plugin-level, Edit mode):

    rojo build giants-preview.project.json -o preview-check.rbxl
    run-in-roblox --place preview-check.rbxl --script tools/giants/checks/<name>.luau

- `standing-animating.luau` — spawns everything via the preview module, starts simulation,
  and asserts every prefab spawn (26 giants × the 5 sizes in `preview.luau` `SCALES`) stands
  at its expected height with the idle track playing and accessories attached. Expect
  `standing+animating+intact=130`.
- `scaleto-probe.luau` — prints what `Model:ScaleTo` changes on the untouched source Baron
  (the reference for what offline scaling must mirror).
- `spawn-size-probe.luau` — prints head/arm sizes before and after parenting, to see whether
  the engine rescales parts at spawn (it does not).
- `animation-scale-probe.luau` — frozen-pose joint displacement at 4× relative to 1× for a
  stock R15, the source Noob and the prefab Noob, under `ScaleTo`, Humanoid scale values and
  `ScaleTo` plus the preview's Transform fix-up. This is the repro for the Animator scaling
  translations by the scale squared on `ScaleTo`'d rigs; expect `head=15.71×` for ScaleTo and
  `4.00×` for the other two. Re-run after engine updates (see `docs/giant-scaling.md` §6).
- `wraplayer-probe.luau` — prints Size / MeshSize (the scriptable mirror of the hidden
  InitialSize) / OriginalSize for every mesh part of the source Baron before and after
  `ScaleTo(1)`, and for the prefab. This is where the layered-clothing rule was measured:
  ScaleTo never resizes a WrapLayer handle, and the engine swaps its AccessoryWeld for an
  AccessoryRigidConstraint on load.

Gotchas: the script runs before any place Script; `RunService:Run()` then executes them all,
so these destroy `GiantsPreviewRun` first. run-in-roblox listens on a fixed port (50312) and
refuses to start while old sockets sit in TIME_WAIT — wait until
`netstat -ano | grep 127.0.0.1:50312` is empty.
