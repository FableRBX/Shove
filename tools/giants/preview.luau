--[[
	Giant prefab preview (giants-preview.project.json). `spawnAll` clones every prefab in
	ServerStorage.Giants the way the game will use it — Model:ScaleTo plus the per-frame
	Animator fix-up in scaleGiant, PivotTo onto the floor, R15 idle animation on its
	Animator — as a grid: one column per giant in roster order along +X
	(COLUMN_SPACING studs apart), one row per entry in SCALES going back along +Z, so each
	column shows the same giant growing from 1× to the largest size the game is likely to
	ask for. In front of the 1× row stand a few untouched source rigs as the engine's own
	reference rendering (see spawnComparisons). Run by preview-run.server.luau on Play; also
	driven headlessly by the import checks. Nothing here is game code.
]]
local RunService = game:GetService("RunService")
local ServerStorage = game:GetService("ServerStorage")
local Workspace = game:GetService("Workspace")

local IDLE_ANIMATION = "rbxassetid://507766666" -- Roblox default R15 idle
-- Sizes to preview per giant; the row spacing below leaves room for the next row's height.
local SCALES = { 1, 1.5, 2.5, 4, 6 }
local ROW_Z = { 0, 18, 42, 80, 136 }
local COLUMN_SPACING = 24 -- wide enough for a 6× giant and its weapon
-- Engine-reference rows, in front of the grid (negative Z).
local REFERENCE_Z = { scaledTo1 = -16, asIs = -34 }

local Preview = {}

local function label(model: Model, text: string)
	local gui = Instance.new("BillboardGui")
	gui.Size = UDim2.fromScale(10, 2)
	gui.StudsOffsetWorldSpace = Vector3.new(0, 2.5, 0)
	gui.AlwaysOnTop = true
	gui.MaxDistance = 400
	local textLabel = Instance.new("TextLabel")
	textLabel.Size = UDim2.fromScale(1, 1)
	textLabel.BackgroundTransparency = 1
	textLabel.TextScaled = true
	textLabel.TextColor3 = Color3.new(1, 1, 1)
	textLabel.TextStrokeTransparency = 0
	textLabel.FontFace = Font.fromEnum(Enum.Font.GothamBold)
	textLabel.Text = text
	textLabel.Parent = gui
	gui.Adornee = model:FindFirstChild("Head")
	gui.Parent = model
end

local function sortedPrefabs(): { Model }
	local prefabs = ServerStorage.Giants:GetChildren()
	table.sort(prefabs, function(a, b)
		return (a:GetAttribute("RosterIndex") or 0) < (b:GetAttribute("RosterIndex") or 0)
	end)
	return prefabs
end

-- Sizing a giant. Two engine facts, both measured in Studio (GIANTS-IMPORT-HANDOFF.md §0b):
--  1. Layered clothing only keeps fitting when the character model's ScaleFactor carries
--     the size, i.e. Model:ScaleTo. Sizing through the Humanoid's Body*Scale values leaves
--     ScaleFactor at 1 and the fit is attempted at world size against native-size cages;
--     jackets and armour vanish from about 3× up.
--  2. The Animator multiplies keyframe translations by ScaleFactor on top of the rig's own
--     k× geometry, so a ScaleTo'd rig animates with k² joint translations: heads float off
--     or sink into collars, arms swing wide, worse the larger k (15.7× at 4×, 35× at 6×).
-- So: ScaleTo for size, then undo the Animator's extra factor every frame by dividing each
-- joint Transform translation by the model's scale on RunService.Stepped, which runs
-- after animation and before physics. Result: joint displacement exactly k× the 1× rig at
-- 2.5, 4 and 6, garments intact at 6. The game needs the same fix-up for every giant it
-- sizes (a Stepped loop over the live giants, as below).
-- The prefabs are jointed with Motor6Ds; characters the engine builds itself (player
-- avatars, CreateHumanoidModelFromDescription) use AnimationConstraints instead. Both
-- carry the Transform the Animator writes, so the fix-up covers both.
type AnimatedJoint = Motor6D | AnimationConstraint
local scaledGiants: { [Model]: { AnimatedJoint } } = {}
local function collectJoints(giant: Model): { AnimatedJoint }
	local joints = {}
	for _, descendant in giant:GetDescendants() do
		if descendant:IsA("Motor6D") or descendant:IsA("AnimationConstraint") then
			table.insert(joints, descendant)
		end
	end
	return joints
end
local function scaleGiant(giant: Model, scale: number)
	giant:ScaleTo(scale)
	if scale == 1 then
		return
	end
	scaledGiants[giant] = collectJoints(giant)
	giant.DescendantAdded:Connect(function(descendant)
		if (descendant:IsA("Motor6D") or descendant:IsA("AnimationConstraint")) and scaledGiants[giant] then
			scaledGiants[giant] = collectJoints(giant)
		end
	end)
	giant.Destroying:Once(function()
		scaledGiants[giant] = nil
	end)
end
Preview.scaleGiant = scaleGiant

RunService.Stepped:Connect(function()
	for giant, joints in scaledGiants do
		local scale = giant:GetScale()
		for _, joint in joints do
			local transform = joint.Transform
			joint.Transform = transform.Rotation + transform.Position / scale
		end
	end
end)

local function spawnGiant(container: Folder, prefab: Model, scale: number, x: number, z: number, caption: string)
	local giant = prefab:Clone()
	local humanoid = giant:FindFirstChildOfClass("Humanoid") :: Humanoid
	local root = giant.PrimaryPart :: BasePart
	giant:SetAttribute("PreviewKind", "prefab")
	giant:SetAttribute("PreviewScale", scale)
	giant.Parent = container
	if scale ~= 1 then
		scaleGiant(giant, scale)
	end
	-- Feet on the floor: the HRP sits HipHeight above the ground plus half its own height.
	giant:PivotTo(CFrame.new(x, humanoid.HipHeight + root.Size.Y / 2, z))
	local animation = Instance.new("Animation")
	animation.AnimationId = IDLE_ANIMATION
	local track = (humanoid:FindFirstChildOfClass("Animator") :: Animator):LoadAnimation(animation)
	track.Looped = true
	track:Play()
	label(giant, `{giant:GetAttribute("DisplayName")} · {caption}`)
	return giant
end

function Preview.spawnAll(): Folder
	local container = Instance.new("Folder")
	container.Name = "Preview"
	container.Parent = Workspace

	local prefabs = sortedPrefabs()
	for i, prefab in prefabs do
		local x = (i - 1) * COLUMN_SPACING
		for row, scale in SCALES do
			spawnGiant(container, prefab, scale, x, ROW_Z[row], `×{scale}`)
		end
	end
	print(`[giants-preview] spawned {#prefabs} giants × {#SCALES} sizes`)
	Preview.spawnComparisons(container)
	return container
end

-- Re-attach every accessory through the engine's own path instead of the prefab's welds.
local function reattachAccessories(giant: Model)
	local humanoid = giant:FindFirstChildOfClass("Humanoid") :: Humanoid
	for _, accessory in giant:GetChildren() do
		if accessory:IsA("Accessory") then
			accessory.Parent = nil
			for _, weld in accessory.Handle:GetChildren() do
				if weld:IsA("Weld") then weld:Destroy() end
			end
			humanoid:AddAccessory(accessory)
		end
	end
end

-- Untouched source rigs (ServerStorage.GiantSources) in front of their prefabs, as the
-- engine's own reference for a correctly rendered giant: REFERENCE_Z.scaledTo1 is the source
-- shrunk to 1× by Model:ScaleTo (compare with the ×1 row right behind it), REFERENCE_Z.asIs
-- is the source at its original size. A prefab that looks different from the ScaleTo'd source
-- is a pipeline regression. Only the giants listed in import_giants.py PREVIEW_SOURCE_IDS are
-- staged.
function Preview.spawnComparisons(container: Folder)
	local sources = ServerStorage:FindFirstChild("GiantSources")
	if not sources then
		return
	end
	for i, prefab in sortedPrefabs() do
		local source = sources:FindFirstChild(prefab.Name)
		if not source then
			continue
		end
		local x = (i - 1) * COLUMN_SPACING
		local sourceScale = prefab:GetAttribute("SourceScale") or 1
		for _, variant in {
			{ z = REFERENCE_Z.scaledTo1, scale = 1 / sourceScale, caption = `source ScaleTo → 1× (engine reference)` },
			{ z = REFERENCE_Z.asIs, scale = 1, caption = `source ×{sourceScale} as-is (engine reference)` },
		} do
			local giant = source:Clone()
			giant:SetAttribute("PreviewKind", "reference")
			giant.Parent = container
			for _, d in giant:GetDescendants() do
				if d:IsA("BasePart") then d.Anchored = false end
			end
			reattachAccessories(giant)
			if variant.scale ~= 1 then
				-- ScaleTo is absolute and the source model already reports its own scale
				giant:ScaleTo(giant:GetScale() * variant.scale)
			end
			local humanoid = giant:FindFirstChildOfClass("Humanoid") :: Humanoid
			local root = giant:FindFirstChild("HumanoidRootPart") :: BasePart
			root.CFrame = CFrame.new(x, humanoid.HipHeight + root.Size.Y / 2 + 0.5, variant.z)
			label(giant, `{prefab:GetAttribute("DisplayName")} · {variant.caption}`)
		end
	end
end

return Preview
