local RunService = game:GetService("RunService")
local ServerStorage = game:GetService("ServerStorage")
local ServerScriptService = game:GetService("ServerScriptService")

if not ServerStorage:FindFirstChild("GiantSources") then
	-- run-in-roblox's plugin is loaded by every open Studio; stay idle in any other place.
	while true do task.wait(60) end
end
ServerScriptService.GiantsPreviewRun:Destroy() -- RunService:Run() would execute it and double-spawn
local prefabs = ServerStorage.Giants:GetChildren()
local preview = require(ServerScriptService.GiantsPreview).spawnAll()
RunService:Run() -- edit-mode plugin context: start physics + animation stepping (F8)
task.wait(3)

local ok, problems = 0, {}
local scales = {}
for _, giant in preview:GetChildren() do
	if giant:GetAttribute("PreviewKind") ~= "prefab" then continue end -- engine-reference rows
	local size = giant:GetAttribute("PreviewScale") or 1
	scales[size] = (scales[size] or 0) + 1
	local hum = giant:FindFirstChildOfClass("Humanoid")
	local root = giant.PrimaryPart
	local expectedY = hum.HipHeight + root.Size.Y / 2
	local y = root.Position.Y
	local tracks = hum:FindFirstChildOfClass("Animator"):GetPlayingAnimationTracks()
	local playing = #tracks > 0 and tracks[1].IsPlaying and tracks[1].Length > 0
	local state = hum:GetState().Name
	local issues = {}
	if math.abs(y - expectedY) > 0.75 then table.insert(issues, string.format("root y %.2f (expected %.2f)", y, expectedY)) end
	if not playing then table.insert(issues, "idle not playing") end
	if state ~= "Running" and state ~= "Landed" then table.insert(issues, "state " .. state) end
	-- every accessory handle must have followed its body part (welded, not fallen off)
	for _, acc in giant:GetChildren() do
		if acc:IsA("Accessory") then
			local handle = acc:FindFirstChild("Handle")
			if handle and (handle.Position - root.Position).Magnitude > 12 * size then
				table.insert(issues, "accessory drifted: " .. acc.Name)
			end
		end
	end
	if #issues > 0 then
		table.insert(problems, string.format("%s ×%.3g: %s", giant.Name, size, table.concat(issues, ", ")))
	else
		ok += 1
	end
end
RunService:Stop()
local sizes = {}
for s in scales do table.insert(sizes, s) end
table.sort(sizes)
local perSize = {}
for _, s in sizes do table.insert(perSize, string.format("x%g:%d", s, scales[s])) end
print(string.format("prefabs=%d spawned=%d standing+animating+intact=%d  per size: %s", #prefabs, #preview:GetChildren(), ok, table.concat(perSize, " ")))
for _, p in problems do print("  PROBLEM " .. p) end
