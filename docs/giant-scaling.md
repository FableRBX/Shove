# Giant prefabs and runtime scaling

Reference for the giant assets under `assets/ServerStorage/Giants/` and for sizing
them at runtime. Everything here was measured in Roblox Studio on 2026-09-22 with
the scripts under `tools/giants/checks/`; where a statement is inference rather
than measurement it says so. Read this before writing the giant spawning code.

## 1. Summary

- The 26 prefabs are normalised R15 characters at base scale 1× with feet on
  y = 0. They map to `ServerStorage.Giants.<Id>` (section 2).
- Two engine behaviours decide how a giant may be sized (section 4):
  1. **Layered clothing** (the WrapLayer garments 14 giants wear) only keeps
     fitting at large sizes when `Model.ScaleFactor` carries the size, i.e.
     after `Model:ScaleTo`. Sizing through the Humanoid's body-scale values loses
     garments from about 4× up. Roblox acknowledges this bug and names `ScaleTo`
     as the workaround.
  2. **Animation** on a `ScaleTo`'d Humanoid rig moves joints by the scale
     squared, not the scale. A stock R15 rig built by the engine shows it too, so
     it is engine behaviour, not something in our prefabs. The body-scale values
     path animates correctly.
- The only combination measured to give both fitted garments and correct
  animation at 4× and 6× is `ScaleTo` plus a per-frame fix-up that divides each
  `Motor6D.Transform` translation by the model's scale (section 5). Up to 2.5×
  the body-scale values path needs no fix-up and every garment fitted.
- Caveats before building on either (section 6): all measurements are from
  Studio, not a live server; `Motor6D.Transform` does not replicate, so the fix-up
  must run on every client; this corner of the engine had bug reports and fixes
  in April and May 2026, so re-measure with `animation-scale-probe.luau` before
  trusting the numbers on a new engine version.
- Open decision for the game (section 7): the largest absolute giant size. If it
  stays around 2.5× the values path is clean and the fix-up can be deleted.

## 2. The assets

| What                                      | Where                                                                                             |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------- |
| Prefabs (26 × `.rbxm`, ~850 KB)           | `assets/ServerStorage/Giants/<Id>.rbxm` → `ServerStorage.Giants.<Id>` (`default.project.json`)    |
| Roster (id, display name, height, source) | `docs/giants-roster.md`, generated                                                                |
| Importer / normaliser                     | `tools/giants/import_giants.py` (`ROSTER` table at the top); shared toolkit `tools/lib/rigs.py`   |
| Converter and second validation pass      | `tools/giants/convert.luau` (lune)                                                                |
| Preview place                             | `giants-preview.project.json`, `tools/giants/preview.luau`; every giant at ×1, ×1.5, ×2.5, ×4, ×6 |
| In-engine checks and probes               | `tools/giants/checks/` (see its README)                                                           |
| Unit tests for the toolkit                | `python -m unittest discover -s tools/lib`                                                        |
| Sources                                   | Phoenix zone enemies and DungeonFall rigs in the sibling repos; see the roster's Source column    |

Regenerate everything with `python tools/giants/import_giants.py` (needs `lune` on
the path and `npx prettier`). Open the preview with
`node ~/.claude/skills/rojo-dev-loop/scripts/dev-loop.js giants-preview --no-serve`.

### 2.1 What a prefab contains

- The 15 R15 body parts plus `HumanoidRootPart`, all 15 Motor6Ds rebuilt from the
  `<Joint>RigAttachment` pairs, `PrimaryPart` = HRP, `ScaleFactor` = 1,
  `WorldPivotData` and HRP `PivotOffset` removed (pivot = HRP centre).
- `Humanoid` with a fresh `Animator`, `RigType` R15, `HipHeight` recomputed from
  the geometry, name and health displays off, and the engine's avatar-scaling
  bookkeeping kept: the `BodyWidthScale` / `BodyHeightScale` / `BodyDepthScale` /
  `HeadScale` NumberValues (1 at base scale), `BodyTypeScale`,
  `BodyProportionScale`, and every part's `OriginalSize` / attachment
  `OriginalPosition` value. Stripping that bookkeeping breaks layered-clothing
  fitting even at the source scale.
- Accessories welded to their attachment pairs with an `AccessoryWeld`, handles
  massless and non-colliding. On load the engine replaces a layered-clothing
  garment's weld with an `AccessoryRigidConstraint` and positions the handle
  itself, so the weld values on garments only matter until the model is loaded.
- Rest pose re-solved from the joint graph, HRP at the origin, feet on y = 0,
  everything unanchored.
- Attributes on the model: `DisplayName`, `Source`, `SourcePath`, `SourceScale`
  (the size the rig had in its source game), `SourceSize`, `Zone`, `Height` (body
  height in studs at 1×), `RosterIndex` (progression order).
- Stripped: scripts, `AnimSaves`, `Sound`s, `HumanoidDescription`, weapon trails
  disabled.

### 2.2 Spawning contract

```lua
local giant = ServerStorage.Giants[id]:Clone()
giant.Parent = workspace
scaleGiant(giant, k)                     -- section 5; k = 1 is a no-op
local humanoid = giant:FindFirstChildOfClass("Humanoid")
local root = giant.PrimaryPart
-- feet on the floor: HRP centre sits HipHeight + half the HRP height above it
giant:PivotTo(CFrame.new(x, floorY + humanoid.HipHeight + root.Size.Y / 2, z))
local track = humanoid.Animator:LoadAnimation(animation)
track:Play()
```

`tools/giants/preview.luau` is the reference implementation of all of this,
including `scaleGiant`.

## 3. How the prefabs were made and what went wrong on the way

Every giant came from a rig that its source game had already scaled (0.8× to
2.03×). The importer shrinks it back to 1× offline, mirroring what
`Model:ScaleTo` does, so that one base scale and one `ScaleTo` factor drive size
at runtime. Two things about that offline scaling were not obvious and cost the
most time:

1. **Layered-clothing handles must not be resized.** A garment is a `MeshPart`
   handle with a `WrapLayer` child. The engine keeps that handle at the garment
   mesh's native size at every body scale: in the sources all 18 garment handles
   have `Size == InitialSize == OriginalSize` regardless of the body being 0.99×
   or 2×, and `ScaleTo(1)` on a 2× source halves every body part, rigid accessory
   and attachment but leaves the garment handle's `Size` alone. A `MeshPart` is
   drawn at `Size / InitialSize` (`MeshSize` is the scriptable mirror of the
   hidden `InitialSize`), so shrinking a garment handle to half makes the engine
   draw the garment at half scale and the fit collapses into floating plates.
   Shrinking `InitialSize` as well "fixes" the garment by restoring the ratio
   while doubling every head for the same reason. `scale_rig` in `rigs.py` now
   skips `size` on WrapLayer handles; both validators reject a garment whose
   `Size` differs from `InitialSize`.
2. **The avatar-scaling bookkeeping is load-bearing.** `OriginalSize`,
   `OriginalPosition`, `AvatarPartScaleType` and the Humanoid's scale values
   looked like leftovers to strip. Stripping them breaks layered clothing even
   at source scale (found by bisecting the pipeline in-engine).

`GIANTS-IMPORT-HANDOFF.md` at the repo root keeps the full timeline.

## 4. Engine behaviour, as measured

All measurements: Studio, run-in-roblox in edit mode with `RunService:Run()`, the
default R15 idle `rbxassetid://507766666`. Animation numbers use a frozen pose
(`AnimationTrack.TimePosition` fixed, `AdjustSpeed(0)`) and compare each joint's
displacement from its rest position with the same rig at 1×.

### 4.1 `Model:ScaleTo` on a Humanoid rig

`ScaleTo(1)` on the 2× source Baron (`checks/scaleto-probe.luau`,
`checks/wraplayer-probe.luau`):

| Property                                                           | Effect               |
| ------------------------------------------------------------------ | -------------------- |
| `BasePart.Size`, `CFrame`, `PivotOffset`, `JointOffset`            | ×0.5                 |
| `Attachment.Position` (body parts and handles)                     | ×0.5                 |
| Motor6D / Weld `C0`, `C1`                                          | ×0.5                 |
| `Humanoid.HipHeight`                                               | ×0.5                 |
| `BodyWidthScale`, `BodyHeightScale`, `BodyDepthScale`, `HeadScale` | 2 → 1                |
| `BodyTypeScale`, `BodyProportionScale`                             | unchanged            |
| `OriginalSize`, `OriginalPosition`, `InitialSize` / `MeshSize`     | unchanged            |
| WrapLayer handle `Size`                                            | **unchanged**        |
| `Model.ScaleFactor`                                                | set to the new scale |

`ScaleTo` is absolute: it sets `ScaleFactor`, so a model that already carries a
factor scales relative to its 1× geometry, not its current size. Phoenix's
sources carried 1.25 / 1.5 / 2 / 0.9 from their own `ScaleTo` calls; the
importer removes the factor so a prefab reads 1.

### 4.2 Animation under the two scaling paths

Joint displacement relative to the same rig at 1× (`checks/animation-scale-probe.luau`):

| Path                                        | k = 2.5 | k = 4 | k = 6 |
| ------------------------------------------- | ------- | ----- | ----- |
| `ScaleTo(k)` — head                         | 6.15    | 15.71 | 35.32 |
| `ScaleTo(k)` — hand                         | 2.19    | 3.59  | 6.77  |
| `ScaleTo(k)` — foot                         |         | 9.01  | 21.31 |
| Humanoid values ×k — head, hand, foot       | 2.50    | 4.00  | 6.00  |
| `ScaleTo(k)` + Transform fix-up (section 5) |         | 4.00  | 6.00  |

The `ScaleTo` head figures are k² within rounding; hand and foot differ because
their keyframes are mostly rotation. Visible result: heads float above the body
(Winter Assassin) or sink into collars and hoods (Ice King, Doom Boss), arms
swing wide, worse the larger k. A stock R15 rig created with
`Players:CreateHumanoidModelFromDescription` gives the identical numbers, as does
the untouched Phoenix source rig, so this is engine behaviour, not a prefab
artefact.

Nothing scriptable other than `ScaleFactor` changes it. Each of these left the
k² in place: resetting the four Humanoid scale values to 1 with
`AutomaticScalingEnabled` off, rewriting `OriginalSize` / `OriginalPosition` to
the scaled values or multiplying them by k with automatic scaling on, removing
them, dividing `HipHeight`, loading the track before scaling. Moving the scaled
parts into a fresh `Model` (so `ScaleFactor` reads 1) restores k×, and a wrapper
model at factor k around a character model at factor 1 also animates at k×; the
factor that matters is the one on the model the Humanoid lives in.

Inference: Roblox's scale API says the Animator keys into model scale to scale
animation playback, and the engine also scales keyframe translations for scaled
avatars; on a `ScaleTo`'d rig both apply. Whether that is intended or a current
regression is not known; see section 6.

### 4.3 Layered clothing under the two scaling paths

Window captures of Winter Assassin (Shinobi jacket and pants), Ice King (Paladin
armour), Desert General (Executioner armour), Sand Mage (Royal jacket), Baron,
Cyber Lord, Leaf Ninja, Doom Boss at 2.5×, 4×, 4.5×, 5×, 5.5×, 6×:

| Path                                             | 2.5×    | 4× and up                                                                    |
| ------------------------------------------------ | ------- | ---------------------------------------------------------------------------- |
| `ScaleTo(k)` (factor k)                          | all fit | all fit, through 6×                                                          |
| Humanoid values ×k (factor 1)                    | all fit | Shinobi jacket/pants, Paladin, Executioner gone; Royal jacket survives to 6× |
| Values ×k plus garment handle `Size` ×k          | all fit | same losses as values alone                                                  |
| Values ×k, garments re-added with `AddAccessory` | all fit | same losses                                                                  |

On the values path the failed garment vanishes; the body parts under it draw
normally. Roblox's bug reports on layered clothing at scale describe the same
thing above a scale value of 5 and state that `ScaleTo` works after their
December 2024 fix while the description and NumberValue methods were still broken;
we see it from about 4× on some garments. The 1× fitting threshold is garment
dependent. This is also why the earlier attempt to fix animation by using the
values path for everything failed in the preview.

### 4.4 Other facts worth keeping

- The engine positions a layered-clothing handle itself on load: the handle
  centre relative to the torso was identical for a prefab, the untouched source,
  and both scaling paths, whatever the stored weld said.
- The engine does not resize parts when a model is parented; sizes are identical
  before and after spawn.
- Head placement is authored per rig. Ice King's head sits low against a tall
  Paladin collar in the untouched source as well; it is the asset's design.
- 130 spawns (26 giants × 5 sizes) stand at the expected height with the idle
  playing and every accessory attached, on both paths.

## 5. The `ScaleTo` + Transform fix-up

Reference implementation: `scaleGiant` in `tools/giants/preview.luau`.

```lua
local scaledGiants: { [Model]: { Motor6D | AnimationConstraint } } = {}

local function scaleGiant(giant: Model, scale: number)
	giant:ScaleTo(scale)
	if scale == 1 then return end
	local joints = {}
	for _, d in giant:GetDescendants() do
		if d:IsA("Motor6D") or d:IsA("AnimationConstraint") then table.insert(joints, d) end
	end
	scaledGiants[giant] = joints
	giant.Destroying:Once(function() scaledGiants[giant] = nil end)
end

RunService.Stepped:Connect(function()
	for giant, joints in scaledGiants do
		local scale = giant:GetScale()
		for _, joint in joints do
			local t = joint.Transform
			joint.Transform = t.Rotation + t.Position / scale
		end
	end
end)
```

Why `Stepped`: the Animator writes each joint's `Transform` every frame before
`Stepped`, and physics reads it after, so this is the window in which the value
can be corrected without fighting either. Cost: 15 CFrame writes per scaled giant
per frame. Rotation is left alone; only the translation is over-scaled.

Both joint classes matter. The prefabs are jointed with Motor6Ds; characters the
engine builds itself (player avatars, `CreateHumanoidModelFromDescription`) have
no Motor6Ds at all and use `AnimationConstraint`s, which carry the same
`Transform`. A fix-up that only collects Motor6Ds silently does nothing on an
engine-built rig, which is how the probe first caught this.

Where it must run: everywhere an Animator evaluates the giant. `Transform` is not
replicated. In a live game the server plays the track and each client evaluates
the animation locally, so the loop is needed on every client for what players
see and on the server for anything that reads the server's part positions. The
preview place demonstrates only the single-DataModel case.

## 6. Caveats

- **Studio only.** Every number above comes from Studio (edit-mode simulation
  and Play). A May 2026 engine-bug thread about animations not transforming with
  model scale notes that Studio and live servers behaved differently. Verify both
  the doubling and the fix-up in a published test place before shipping either.
- **The engine is moving.** Reports from April and May 2026 cover model scale
  being applied unevenly to joints in animations (resolved itself in a Studio
  update) and animations not transforming with model scale (fixed by Roblox on
  May 20, 2026). The k² we measure may be a current regression. If Roblox fixes
  it, a blind divide over-corrects; see section 7 for how to guard against that.
- **Garment threshold is per garment.** 4× is where the first garments failed on
  the values path here; do not assume 5 from the forum threads.
- **Run-in-roblox hazard.** Its plugin loads into every open Studio; close other
  Studio windows before running the checks (details in `checks/README.md`).

## 7. Options for the game, and a recommendation

1. **Cap giant scale where the values path works.** At 2.5× every garment fitted
   and animation was exact with no fix-up. If the largest absolute giant the game
   needs is around that (the GDD's opponent target is 1.5–2.5× the player, but
   the player also grows), size through the four Humanoid scale values and
   delete the fix-up. Cleanest option; depends on a design number.
2. **`ScaleTo` plus the fix-up, made defensive.** Keep section 5 but gate it
   behind a config flag and a one-time runtime probe: spawn a hidden reference
   rig at 1× and one at k, freeze the same track, compare a joint translation, and
   apply the division only if the ratio is k² rather than k. Then a future engine
   fix turns the workaround off by itself.
3. **Report the bug.** `checks/animation-scale-probe.luau` on a stock rig is a
   clean minimal repro.
4. **Replace the layered clothing** on the 14 affected giants with rigid or
   classic clothing. Removes the constraint at the cost of art work.

Recommendation: 1 if the scale budget allows it, otherwise 2 with 3, and a live
server check in either case. The decision that unblocks the giant service is the
maximum absolute giant scale.

## 8. Sources

- [Layered clothing disappears if the character's scale value greater than 5](https://devforum.roblox.com/t/layered-clothing-disappears-if-the-characters-scale-value-greater-than-5-500/3180989)
  — staff: change rolled back, further fixes promised (October 2024).
- [Layered Clothing Doesn't Work At Large Scales](https://devforum.roblox.com/t/layered-clothing-doesnt-work-at-large-scales/3224292)
  — staff: `ScaleTo` fixed December 7, 2024; description and NumberValue methods
  still broken as of December 12, 2024.
- [Animations No Longer Transform With Model Scale](https://devforum.roblox.com/t/animations-no-longer-transform-with-model-scale/4637091)
  — May 2026; Studio and live differed; fixed by staff May 20, 2026.
- [Model Scale property erroneously stopped being applied properly uniformly in Animations](https://devforum.roblox.com/t/model-scale-property-errenously-stopped-being-applied-properly-uniformly-in-animations/4603234)
  — April 2026; torso offsets not scaled; resolved in a later Studio build.
- [Animation Scaling feature thread](https://devforum.roblox.com/t/animation-scaling/1812612)
  and the March 2023 Model Scale API announcement it references.
