local RunService = game:GetService("RunService")
local ServerStorage = game:GetService("ServerStorage")
ServerScriptService = game:GetService("ServerScriptService")
ServerScriptService.GiantsPreviewRun:Destroy()
local function snap(m, tag)
	local hum = m:FindFirstChildOfClass("Humanoid")
	local vals = {}
	for _, v in hum:GetChildren() do if v:IsA("NumberValue") then vals[#vals+1] = v.Name:gsub("Scale",""):gsub("Body","") .. "=" .. string.format("%.3g", v.Value) end end
	table.sort(vals)
	local function sz(p) return string.format("(%.2f,%.2f,%.2f)", p.Size.X, p.Size.Y, p.Size.Z) end
	local function os_(p) local o = p:FindFirstChild("OriginalSize"); return o and string.format("(%.2f,%.2f,%.2f)", o.Value.X, o.Value.Y, o.Value.Z) or "-" end
	print(string.format("%-34s Head %s orig %s | Arm %s orig %s | HRP %s | %s", tag, sz(m.Head), os_(m.Head), sz(m.LeftUpperArm), os_(m.LeftUpperArm), sz(m.HumanoidRootPart), table.concat(vals, " ")))
end
local function test(model, tag, scaleTo)
	local m = model:Clone()
	snap(m, tag .. " [file]")
	m.Parent = workspace
	if scaleTo then m:ScaleTo(scaleTo) end
	task.wait(0.5)
	snap(m, tag .. " [spawned]")
	m:Destroy()
end
RunService:Run()
test(ServerStorage.Giants.Viking, "prefab Viking")
test(ServerStorage.Giants.Noob, "prefab Noob")
test(ServerStorage.GiantSources.Baron, "source Baron 2x")
test(ServerStorage.GiantSources.Baron, "source Baron ScaleTo(1)", 1)
test(ServerStorage.Giants.Baron, "prefab Baron")
test(ServerStorage.Giants.Knight, "prefab Knight (DF)")
RunService:Stop()
