-- How much does the Animator move a joint on a scaled rig, relative to the same rig at 1x?
-- Frozen idle pose (fixed TimePosition, speed 0), three rig origins x three paths:
--   stock R15 built by the engine, untouched Phoenix source Noob, prefab Noob
--   ScaleTo(k), Humanoid scale values x k, ScaleTo(k) + the preview's Transform fix-up
-- Expected: values = k; ScaleTo = k^2 on the head while the engine double-scales (Sep 2026);
-- ScaleTo + fix-up = k. Re-run after an engine update before trusting docs/giant-scaling.md.
if not game:GetService("ServerStorage"):FindFirstChild("GiantSources") then
	-- run-in-roblox's plugin is loaded by every open Studio; stay idle in any other place.
	while true do task.wait(60) end
end
local RunService = game:GetService("RunService")
local ServerStorage = game:GetService("ServerStorage")
local ServerScriptService = game:GetService("ServerScriptService")
local Players = game:GetService("Players")
ServerScriptService.GiantsPreviewRun:Destroy()
local Preview = require(ServerScriptService.GiantsPreview)

local IDLE = "rbxassetid://507766666"
local FREEZE_AT = 0.9
local K = 4
local VALUES = { "BodyWidthScale", "BodyHeightScale", "BodyDepthScale", "HeadScale" }

local folder = Instance.new("Folder")
folder.Name = "AnimationScaleProbe"
folder.Parent = workspace

local function humanoidOf(m) return m:FindFirstChildOfClass("Humanoid") end
local function stand(m, x, z)
	local h = humanoidOf(m)
	local root = m.HumanoidRootPart
	root.CFrame = CFrame.new(x, h.HipHeight + root.Size.Y / 2 + 0.1, z)
end
local function scaleByValues(m, k)
	local h = humanoidOf(m)
	for _, n in VALUES do
		local v = h:FindFirstChild(n)
		if not v then
			v = Instance.new("NumberValue")
			v.Name = n
			v.Value = 1
			v.Parent = h
		end
		v.Value *= k
	end
end

local origins = {}
local ok, stock = pcall(function()
	return Players:CreateHumanoidModelFromDescription(Instance.new("HumanoidDescription"), Enum.HumanoidRigType.R15)
end)
if ok and stock then
	table.insert(origins, { name = "stock R15", make = function() return stock:Clone() end })
else
	print("stock rig unavailable: " .. tostring(stock))
end
table.insert(origins, { name = "source Noob", make = function()
	local m = ServerStorage.GiantSources.Noob:Clone()
	for _, d in m:GetDescendants() do if d:IsA("BasePart") then d.Anchored = false end end
	return m
end })
table.insert(origins, { name = "prefab Noob", make = function() return ServerStorage.Giants.Noob:Clone() end })

local subjects = {}
local function add(m, tag, k, origin, x, z)
	m.Parent = folder
	stand(m, x, z)
	table.insert(subjects, { model = m, tag = tag, k = k, origin = origin })
end
for oi, o in origins do
	local z = (oi - 1) * 40
	add(o.make(), o.name .. " control", 1, o.name, 0, z)
	local p = o.make(); p.Parent = folder; p:ScaleTo(p:GetScale() * K)
	add(p, string.format("%s ScaleTo x%g", o.name, K), K, o.name, 30, z)
	local v = o.make(); v.Parent = folder; scaleByValues(v, K)
	add(v, string.format("%s values x%g", o.name, K), K, o.name, 60, z)
	local f = o.make(); f.Parent = folder; Preview.scaleGiant(f, K * f:GetScale())
	add(f, string.format("%s ScaleTo+fix x%g", o.name, K), K, o.name, 90, z)
end

local function snapshot(m)
	local root = m.HumanoidRootPart
	local rel = function(p) return root.CFrame:PointToObjectSpace(p.Position) end
	return { head = rel(m.Head), hand = rel(m.LeftHand), foot = rel(m.LeftFoot) }
end

RunService:Run()
task.wait(3)
for _, e in subjects do e.static = snapshot(e.model) end
for _, e in subjects do
	local h = humanoidOf(e.model)
	local animator = h:FindFirstChildOfClass("Animator") or Instance.new("Animator", h)
	local anim = Instance.new("Animation")
	anim.AnimationId = IDLE
	local track = animator:LoadAnimation(anim)
	track.Looped = true
	track:Play(0)
	track.TimePosition = FREEZE_AT
	track:AdjustSpeed(0)
end
task.wait(3)
local refs = {}
for _, e in subjects do
	local s, f = e.static, snapshot(e.model)
	e.delta = { head = f.head - s.head, hand = f.hand - s.hand, foot = f.foot - s.foot }
	if e.k == 1 then refs[e.origin] = e.delta end
end
for _, e in subjects do
	local d, r = e.delta, refs[e.origin]
	print(string.format("%-28s GetScale=%.3g  head=%.2f×  hand=%.2f×  foot=%.2f×  (expected %g)",
		e.tag, e.model:GetScale(), d.head.Magnitude / r.head.Magnitude, d.hand.Magnitude / r.hand.Magnitude,
		d.foot.Magnitude / math.max(r.foot.Magnitude, 1e-3), e.k))
end
RunService:Stop()
