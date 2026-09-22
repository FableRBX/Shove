-- What happens to layered-clothing (WrapLayer) handles under the engine's own ScaleTo,
-- versus what the offline pipeline produced. MeshSize is the read-only mirror of the
-- hidden InitialSize, so this also shows whether ScaleTo touches it.
local RunService = game:GetService("RunService")
local ServerStorage = game:GetService("ServerStorage")
local ServerScriptService = game:GetService("ServerScriptService")
ServerScriptService.GiantsPreviewRun:Destroy()

local function v(x) return string.format("(%.3f,%.3f,%.3f)", x.X, x.Y, x.Z) end
local function meshSize(p)
	local ok, r = pcall(function() return p.MeshSize end)
	return ok and v(r) or ("ERR:" .. tostring(r))
end
local function dump(m, tag)
	print(string.format("=== %s  GetScale=%.3g", tag, m:GetScale()))
	local hum = m:FindFirstChildOfClass("Humanoid")
	local vals = {}
	for _, nv in hum:GetChildren() do if nv:IsA("NumberValue") then vals[#vals + 1] = nv.Name .. "=" .. string.format("%.3g", nv.Value) end end
	table.sort(vals)
	print("    humanoid: HipHeight=" .. string.format("%.3f", hum.HipHeight) .. " " .. table.concat(vals, " "))
	for _, d in m:GetDescendants() do
		if d:IsA("MeshPart") or (d:IsA("BasePart") and d.Parent:IsA("Accessory")) then
			local wl = d:FindFirstChildOfClass("WrapLayer")
			local wt = d:FindFirstChildOfClass("WrapTarget")
			local orig = d:FindFirstChild("OriginalSize")
			local sm = d:FindFirstChildOfClass("SpecialMesh")
			print(string.format("  %-9s %-34s Size=%s MeshSize=%s Orig=%s %s%s%s", d.ClassName, d.Parent.Name .. "/" .. d.Name, v(d.Size),
				d:IsA("MeshPart") and meshSize(d) or "-", orig and v(orig.Value) or "-", wl and "WL " or "", wt and "WT " or "", sm and ("SM scale=" .. v(sm.Scale)) or ""))
			if wl or (d.Parent:IsA("Accessory") and d.Parent.Name:find("Hair")) then
				for _, a in d:GetChildren() do
					if a:IsA("Attachment") then
						local op = a:FindFirstChild("OriginalPosition")
						print(string.format("        att  %-24s Pos=%s OrigPos=%s", a.Name, v(a.Position), op and v(op.Value) or "-"))
					elseif a:IsA("Weld") or a:IsA("Motor6D") then
						print(string.format("        weld %-24s C0=%s C1=%s Part1=%s", a.Name, v(a.C0.Position), v(a.C1.Position), a.Part1 and a.Part1.Name or "nil"))
					end
				end
			end
		end
	end
end

local function reattach(giant)
	local humanoid = giant:FindFirstChildOfClass("Humanoid")
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

-- 1. untouched source, engine ScaleTo, no reattach
local src = ServerStorage.GiantSources.Baron:Clone()
src.Parent = workspace
dump(src, "source Baron as stored")
src:ScaleTo(1)
dump(src, "source Baron after ScaleTo(1)")
src:Destroy()

-- 2. what the preview's row 54 does: AddAccessory then ScaleTo
local src2 = ServerStorage.GiantSources.Baron:Clone()
src2.Parent = workspace
for _, d in src2:GetDescendants() do if d:IsA("BasePart") then d.Anchored = false end end
reattach(src2)
dump(src2, "source Baron after AddAccessory (row 36)")
src2:ScaleTo(1)
dump(src2, "source Baron after AddAccessory + ScaleTo(1) (row 54)")

-- 3. the current prefab, before and after simulation starts
local pre = ServerStorage.Giants.Baron:Clone()
pre.Parent = workspace
pre:PivotTo(CFrame.new(20, 5, 0))
dump(pre, "prefab Baron (state D) as stored")
RunService:Run()
task.wait(1)
dump(pre, "prefab Baron (state D) after 1s of simulation")
dump(src2, "source row 54 after 1s of simulation")
RunService:Stop()
