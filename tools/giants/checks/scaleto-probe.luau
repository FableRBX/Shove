local ServerStorage = game:GetService("ServerStorage")
local src = ServerStorage.GiantSources.Baron:Clone()
src.Parent = workspace
local function snap(m)
	local arm = m.LeftUpperArm
	local hum = m:FindFirstChildOfClass("Humanoid")
	local att = arm:FindFirstChild("LeftShoulderRigAttachment")
	local hair
	for _, a in m:GetChildren() do if a:IsA("Accessory") and a.Name:lower():find("hair") then hair = a end end
	local vals = {}
	for _, v in hum:GetChildren() do if v:IsA("NumberValue") then vals[#vals+1] = v.Name .. "=" .. string.format("%.3g", v.Value) end end
	table.sort(vals)
	return string.format(
		"scale=%.3g arm.Size=%s arm.OriginalSize=%s att.Pos=%s att.OriginalPosition=%s HipHeight=%.3f HRP.PivotOffset.Y=%.3f hairHandleSize=%s\n   humanoid values: %s",
		m:GetScale(), tostring(arm.Size), tostring(arm:FindFirstChild("OriginalSize") and arm.OriginalSize.Value),
		tostring(att.Position), tostring(att:FindFirstChild("OriginalPosition") and att.OriginalPosition.Value),
		hum.HipHeight, m.HumanoidRootPart.PivotOffset.Position.Y, hair and tostring(hair.Handle.Size) or "-",
		table.concat(vals, " "))
end
print("BEFORE  " .. snap(src))
src:ScaleTo(1)
print("AFTER   " .. snap(src))
src:Destroy()
