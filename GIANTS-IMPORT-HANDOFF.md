# Giant prefab import — handoff notes

Written 2026-09-22 at the end of a long session. Nothing below is committed yet
(`git status` shows it all as new/modified). Read this before touching
`tools/giants/` or `assets/ServerStorage/Giants/`.

## 0. Resolution (2026-09-22, later session)

> The consolidated reference, with the measurements, the caveats (Studio-only,
> replication, engine in flux) and the options for the game, is `docs/giant-scaling.md`.
> §0 and §0b below are the working notes it was written from.

The layered-clothing bug in §5 is fixed; §5–§6 below are kept as the record of how it
was found. Root cause: `scale_rig` shrank every BasePart, but the engine never resizes a
**layered-clothing handle** (a MeshPart with a `WrapLayer` child). Measured with
`tools/giants/checks/wraplayer-probe.luau`: `Model:ScaleTo(1)` on the 2× source Baron
halves every body part, rigid accessory, attachment and `HipHeight`, yet leaves the
`Warlock` garment handle at its full `Size` (3.12 × 4.27 × 1.80 = its `InitialSize` =
its `OriginalSize`). All 18 garment handles across the 14 affected giants sit at that
same native size in the sources regardless of body scale (0.99×–2.03×). The engine draws
a MeshPart at `Size / InitialSize` (`MeshSize` is the scriptable mirror of the hidden
`InitialSize`); halving the handle made that 0.5 and the fit collapsed. That is also why
state C "worked": halving `InitialSize` too restored the ratio to 1 — while breaking every
head for the same reason.

Confirmed with a one-variable test in Studio: the state-D prefab with only
`Warlock.Handle.Size = Warlock.Handle.MeshSize` renders identically to the engine's
`ScaleTo(1)` reference, and `ScaleTo(2)` on that fixed prefab renders correctly too.

Changes: `scale_rig` skips `size` on WrapLayer handles (everything else about them still
scales, as `ScaleTo` does); `import_giants.validate()` and `convert.luau` both reject a
garment handle whose `Size ≠ InitialSize`; `tools/lib/test_rigs.py` covers the rule
(`python -m unittest discover -s tools/lib`); all 26 prefabs regenerated;
`checks/standing-animating.luau` reports 52/52. The bisect row, the AddAccessory prefab
row and `write_bisect_for_preview` are gone; rows 36/54 (engine reference) stay as the
regression check. Side fact: on load the engine replaces a garment's `AccessoryWeld`
with an `AccessoryRigidConstraint` and positions the handle itself, so the pipeline's
weld C0/C1 on garments only matter until the model is loaded.

## 0b. Runtime scaling: `ScaleTo` plus a per-frame Animator fix-up (2026-09-22, later still)

With the prefabs fixed, the five-size preview showed a second problem that grows with
size: heads float off (Winter Assassin), or sink into layered clothing (Ice King, Doom
Boss, Sand Mage). Everything below was measured in Studio with frozen idle poses
(`AnimationTrack.TimePosition` fixed, `AdjustSpeed(0)`) so joint displacement could be
compared with a 1× control, plus window captures for the garments.

Two engine facts collide on `Model.ScaleFactor`:

1. **The Animator applies `ScaleFactor` on top of the rig's k× geometry.** A `ScaleTo(k)`
   rig animates with k² joint translations (6.2× at 2.5, 15.7× at 4, 35× at 6, all
   against the 1× control). Sizing through the Humanoid's `Body*Scale` values instead
   (`ScaleFactor` stays 1) gives exactly k. The second factor is not the values,
   `OriginalSize`, `HipHeight` or track load order — resetting or removing each of them
   left k²; only the Humanoid's own model's `ScaleFactor` matters (a wrapper model at k
   around a character model at 1 animates correctly).
2. **Layered clothing only keeps fitting when the character model's `ScaleFactor` carries
   the size.** On the values path (or any path with `ScaleFactor` 1: fresh model, wrapper),
   jackets and armour vanish from about 3× up, garment by garment (Sand Mage's robe
   survives 6×, the Shinobi jackets and the Paladin/Executioner armour do not at 4×);
   scaling the garment handle's `Size` with the body does not rescue them. With
   `ScaleFactor` = k every garment fits at 6×, whatever the values or bookkeeping say.

Resolution: size with `Model:ScaleTo(k)` and, every frame on `RunService.Stepped` (after
animation, before physics), replace each `Motor6D.Transform` with its rotation plus its
translation divided by `model:GetScale()`. Measured result: joint displacement exactly k×
the 1× rig (4.00 / 6.00 on head, hand and foot) with every garment intact at 4× and 6×.
`preview.luau` `scaleGiant` is the reference implementation; the game's giant service
needs the same Stepped loop over its live giants. The standing check tags spawns with
`PreviewScale` and expects 130 (26 giants × 5 sizes).

## 1. Goal

Prepare the opponent "giants" for the Push a Giant prototype (see
`docs/push-a-giant-gdd.md`, "The giant encounter" and "Content production"): take
26 humanoid rigs chosen from sibling repos, pull them into this repo as prefabs, and
**normalise them into one consistent R15 character format** so every giant can play
the same animations and behave the same way at runtime.

The GDD gives each giant a data entry that includes its **scale**, so the intended
runtime model is: prefab at a known base scale in `ServerStorage.Giants.<Id>`, the game
clones it, `Model:ScaleTo(k)`, `PivotTo(...)`, plays animations on its `Animator`.

The roster (Id → source) is the `ROSTER` table at the top of
`tools/giants/import_giants.py`, and `docs/giants-roster.md` is generated from it.

## 2. What exists

| Path                                                                                               | What                                                                                                                                                                                                                                                                                                                                                                                      |
| -------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tools/npc-gallery/build.py` + `npc-gallery.project.json`                                          | Stage 1 (done, works): a gallery place of all 162 candidate rigs from gsclassic / Phoenix / DungeonFall on labelled pedestals. `python tools/npc-gallery/build.py`, then `node ~/.claude/skills/rojo-dev-loop/scripts/dev-loop.js npc-gallery --no-serve`.                                                                                                                                |
| `tools/lib/rigs.py`                                                                                | Shared rig toolkit (stdlib Python on Studio `.rbxmx` XML): copy subtrees between files with SharedStrings, rebuild R15 joints from rig attachments, weld accessories from attachment pairs, re-solve rest pose from the joint graph, measure, **`scale_rig`** (offline uniform rescale mirroring `Model:ScaleTo`, see §0), write attributes.                                              |
| `tools/giants/import_giants.py`                                                                    | Stage 2 (done): imports the 26 giants, runs `normalise()`, validates, writes staged `.rbxmx` to `tools/giants/build/` (gitignored), converts to `.rbxm` with lune, writes `docs/giants-roster.md` (prettier-formatted). Also writes `GiantSources.rbxmx` (untouched copies of Baron / DesertGeneral / CyberLord / Noob) for the preview's engine-reference rows and the in-engine probes. |
| `tools/giants/convert.luau`                                                                        | lune: `.rbxmx` → `.rbxm` plus a second validation pass (rig wiring, Animator, no scripts, unanchored, accessories welded, `BodyHeightScale == 1`, layered-clothing handles at `InitialSize`).                                                                                                                                                                                             |
| `assets/ServerStorage/Giants/*.rbxm`                                                               | The 26 prefabs (~850 KB). Mapped to `ServerStorage.Giants` by `default.project.json` (new `ServerStorage` node).                                                                                                                                                                                                                                                                          |
| `giants-preview.project.json`, `tools/giants/preview.luau`, `tools/giants/preview-run.server.luau` | Preview place: on Play, spawns every prefab the way the game will (clone → `ScaleTo` → `PivotTo` → idle animation). Build/open: `node ~/.claude/skills/rojo-dev-loop/scripts/dev-loop.js giants-preview --no-serve`. Row layout below.                                                                                                                                                    |
| `tools/giants/checks/*.luau`                                                                       | run-in-roblox scripts used for in-engine verification and probing (see its README).                                                                                                                                                                                                                                                                                                       |
| `docs/giants-roster.md`                                                                            | Generated table: Id, display name, base height, source scale, accessory count, source path.                                                                                                                                                                                                                                                                                               |

Preview layout: one column per giant along +X in roster order (24 studs apart), one row per
size going back along +Z — ×1 at z = 0, ×1.5 at 18, ×2.5 at 42, ×4 at 80, ×6 at 136 (`SCALES`
/ `ROW_Z` in `preview.luau`). In front of the ×1 row, for the giants in `PREVIEW_SOURCE_IDS`
(Baron, Desert General, Cyber Lord, Ice King, Noob): z = −16 the untouched source shrunk to
1× by the engine's own `ScaleTo` (the reference a ×1 prefab must match), z = −34 the source
at its original size.

## 3. The normalisation pipeline (`normalise()` in import_giants.py)

1. Strip junk: `AnimSaves` models, `Sound`s, `HumanoidDescription`. _(verified harmless: bisect V2 renders correctly)_
2. _(no-op now — used to strip the avatar-scaling bookkeeping; see §5)_
3. Drop Motor6Ds in body parts that are not the 15 R15 joints; disable `Trail`s.
4. Rewire the 15 Motor6Ds from `<Joint>RigAttachment` pairs (Part0/Part1/C0/C1).
5. Weld every Accessory handle to its body attachment with an `AccessoryWeld` (`Part0=Handle, Part1=body part, C0=handle att, C1=body att`). Stale welds pointing outside the model are removed first.
6. Re-solve the rest pose from the joint graph (saved rigs are mid-animation), HRP at origin, feet on y = 0, all parts unanchored.
7. Humanoid cleanup: remove children except the `Body*Scale` NumberValues, add a fresh `Animator`, `RigType=R15`, `HipHeight` recomputed from geometry, `DisplayDistanceType=None`, `HealthDisplayType=AlwaysOff`.
8. Accessory handles `CanCollide=false`, `Massless=true` (what `AddAccessory` does; a heavy handle can become the physics root).
9. `Name=<Id>`, `PrimaryPart=HRP`, remove `WorldPivotData`, remove HRP `PivotOffset` (Phoenix parked the pivot at the feet), remove the model's `ScaleFactor` (Phoenix used `ScaleTo`, so the models carried 1.25/1.5/2/0.9 and `ScaleTo(k)` on the prefab would have been relative to that).
10. **Scale to 1×** with `scale_rig(1 / BodyHeightScale)` — see §5 for what it currently touches.

Attributes written on each model: `DisplayName, Source, SourcePath, SourceScale, SourceSize, Zone, Height, RosterIndex`.

## 4. What is verified and solid

- The joint solver reproduces engine rest poses exactly (0.00 studs on rigs saved at rest; all 154 engine-welded Phoenix accessory handles within 2e-5 studs of my weld placement). Not the problem.
- `tools/giants/checks/standing-animating.luau`: all 52 prefab spawns (26 at 1×, 26 `ScaleTo`'d) stand at the expected height, `Running`/`Landed`, idle track playing, accessories attached, `GetScale()==1` where expected. Physics/animation/structure are fine. **The remaining problem is purely visual.**
- Rigs with only rigid accessories look right at every scale: Noob, Goblin, Viking, Peasant, Sun Gladiator, Red Orc, Featherweight Champ, Buff Noob, Commander, Knight, Mage, Archer (12).
- The engine renders the _untouched_ source rigs correctly, both at source scale and after its own `ScaleTo(1)` (preview rows 36/54). So a correct 1× result is achievable; the offline pipeline just doesn't match what `ScaleTo` does yet.

## 5. The bug (historical — resolved, see §0)

**Symptom:** on the 14 giants that wear **layered clothing** (`WrapLayer` accessories —
Baron, Chaos Mage, Chaos Summoner, Cyber Lord, Demon Ninja, Desert General, Doom Boss,
Fire Troll, Forest Troll, Frost Mage, Ice King, Leaf Ninja, Sand Mage, Winter Assassin)
the body renders as floating flat "plates" (block hands/feet, 1×0.3×1 slabs) with a
garment and head, and no arms/legs. Cause: the garment is not being fitted to the
body's `WrapTarget` cages, so hidden-surface removal hides body faces the garment then
fails to cover. In Baron's source the arms/legs/torso are literally `Transparency=1`
under the outfit, so nothing is left when the outfit fails.

**Timeline of attempts (each verified by the user in the preview):**

| #   | Change                                                                                                                                                                                                                                                 | Result                                                                                                                                               |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| A   | First prefabs: stripped `OriginalSize`, `OriginalPosition`, `AvatarPartScaleType`, Humanoid `Body*Scale` values, `HumanoidDescription`; `scale_rig` scaled `size`, `CFrame`, attachments, joint C0/C1, SpecialMesh, HipHeight; `InitialSize` untouched | Layered-clothing giants broken (plates). Others fine.                                                                                                |
| B   | Added `JointOffset` + `PivotOffset` + **`InitialSize`** to `scale_rig`; bisect row added                                                                                                                                                               | Bisect: V1/V2 fine, **V3 (strip scale values) broken** → the bookkeeping is load-bearing.                                                            |
| C   | Keep `OriginalSize`/`OriginalPosition`/`AvatarPartScaleType`/`Body*Scale`; `scale_rig` now also divides `BodyWidth/Height/Depth/HeadScale` by the factor (mirrors `ScaleTo`, see probe below); `InitialSize` still scaled                              | **Layered clothing fitted correctly**, but every head rendered ~2× too big (hair hidden inside), at 1× and after `ScaleTo`. Body parts looked right. |
| D   | Stopped scaling `InitialSize` (it is the mesh's native size: constant `1.198×1.202×1.198` for the head across Noob/Viking/Baron sources)                                                                                                               | Heads correct again, **layered clothing broken again** (same plates as A). Current state of `assets/`.                                               |

So: with `InitialSize` halved along with `size`, garments fit and heads are wrong; with
`InitialSize` native, heads are right and garments break. `InitialSize` is a hidden
MeshPart property, not scriptable, so it could only be observed in the XML.

**Engine facts measured in-engine (run-in-roblox, `checks/scaleto-probe.luau`,
`checks/spawn-size-probe.luau`):**

- `Model:ScaleTo(1)` on the 2× source Baron: `Size` ×0.5, attachment `Position` ×0.5, `HipHeight` ×0.5, HRP `PivotOffset` ×0.5, accessory handle `Size` ×0.5; Humanoid `BodyWidth/Height/Depth/HeadScale` 2 → 1; **unchanged:** `OriginalSize`, `OriginalPosition`, `BodyTypeScale` (0.6), `BodyProportionScale` (2).
- The engine does **not** rescale parts when a model is parented (sizes identical before/after spawn for prefab and source), so the head-size and garment issues are rendering-side, not the avatar-scaling pass.
- Phoenix parts have `OriginalSize`/`OriginalPosition` but **no** `AvatarPartScaleType` values; the DungeonFall rigs have all of them.
- `JointOffset` scales with the rig in the sources (0.50 → 0.75 → 1.00 for 1×/1.5×/2×); `InitialSize` does not.
- Serialized property spellings in these files: `size`, `InitialSize`, `JointOffset`, `MeshId`/`TextureID` (Phoenix, legacy `<url>`), `MeshContent`/`TextureContent` (gsclassic), `Color3uint8`, `ScaleFactor` on Model, `AttributesSerialize` (binary; encoder in `rigs.py`).

## 6. Where to pick up (historical — resolved, see §0)

**First, look at the bisect row (z = 90) in the current build** — it was regenerated with
the pipeline of state D but nobody has checked it yet. V1–V10 are at _source_ scale, V11
is the scaled prefab. This answers the key question:

- If **V10 looks right and only V11 is broken** → the structural steps are fine and the
  offline scaling is the sole culprit. Then try, in order:
  1. Scale `InitialSize` **only on accessory-handle MeshParts** (garments), not on body
     parts. Rationale: C fixed garments by scaling every `InitialSize`; D broke garments by
     scaling none; the head regression came from body parts. One-line change in
     `scale_rig` (branch on whether the part's parent is an `Accessory`).
  2. If that fails, scale `InitialSize` only on handles that carry a `WrapLayer`.
  3. Diff _everything_ between a state-C prefab and the ScaleTo'd source. There is no way
     to serialize from the engine, but scriptable properties can be printed with
     run-in-roblox (extend `checks/scaleto-probe.luau`: WrapLayer `Puffiness`/`Order`,
     handle `Size`, `AccessoryWeld` C0/C1, `Attachment` positions on handles).
- If **V10 is also broken** → one of steps 3–9 breaks layered clothing even without
  scaling; re-bisect (the row already gives you the step) — most suspicious are 5 (my
  welds vs the engine's) and 7 (Humanoid children).

**Fallback that is known to work:** stop scaling offline. Keep each prefab at its
_source_ scale (the engine renders those correctly, row 36) and let the game call
`Model:ScaleTo(targetScale / SourceScale)` at spawn — the engine's `ScaleTo` on these
rigs is verified correct (row 54). Cost: base heights differ per prefab (5.4–12 studs),
so giant data must be authored in absolute studs or relative to the `Height` attribute
rather than "×k". Implementation: in `normalise()` skip step 10 (`do_scale=False`), keep
`ScaleFactor` removal (it must read 1 for `ScaleTo` to be absolute — verify the engine's
`GetScale()` afterwards; a non-1 `ScaleFactor` made `ScaleTo` relative to the old size
earlier in this work), and change the `BodyHeightScale == 1` validation in
`convert.luau`.

Either way, when it's fixed: delete the diagnostic rows (36–90) from `preview.luau`,
`write_sources_for_preview`/`write_bisect_for_preview` from the importer and their two
entries in `giants-preview.project.json` (or keep one source-vs-prefab row as a
regression check), re-run `python tools/giants/import_giants.py`, run
`checks/standing-animating.luau`, run `npm run lint`, commit.

## 7. Harness pitfalls (cost real time)

- `run-in-roblox` runs the script at plugin level in **Edit mode**. Place `Script`s do not
  run until the script calls `RunService:Run()` — and then _all_ of them do, so the
  preview's `GiantsPreviewRun` double-spawned everything and humanoids stacked on each
  other (read as `Climbing` state / +4 studs). Every check script now destroys that
  Script first.
- `run-in-roblox` uses fixed port 50312; TIME_WAIT sockets from the previous run block
  it for ~30–60 s ("Only one usage of each socket address"). Wait until
  `netstat -ano | grep 127.0.0.1:50312` is empty.
- Python on Windows writes CRLF; the repo's prettier check wants LF. All generators
  write with `newline="\n"`, and the importer runs prettier on the roster doc.
- Each `dev-loop.js` run opens a _new_ Studio; the window whose title matches the file
  the run printed is the live one, older windows are stale builds.

## 8. Other notes

- Sibling repos and what they hold is recorded in the NPC gallery tooling and in Claude's
  project memory (`npc-asset-sources`): gsclassic skins are loose R15 parts (no HRP),
  Phoenix enemies are scaled via `ScaleTo` + Humanoid scale values, DungeonFall has full
  rigs of most catalog bundles, TitanSimulatorX ⊂ Phoenix.
- The gallery (`tools/npc-gallery`) shrinks a few 20–240-stud rigs for display with the
  same `scale_rig`; whatever fix lands in `rigs.py` applies there too (those rigs wear no
  layered clothing, so they are not visibly affected today).
- `npm run lint` passes as of state D.
