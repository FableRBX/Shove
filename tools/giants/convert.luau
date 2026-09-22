--[[
	Convert every staged giant (<stage>/<Id>.rbxmx) to a binary model (<out>/<Id>.rbxm),
	re-checking the rig through rbx_dom on the way (rbx_dom exposes the hidden InitialSize,
	which the engine does not). Driven by import_giants.py:

		lune run tools/giants/convert.luau <stage dir> <out dir>
]]
local fs = require("@lune/fs")
local process = require("@lune/process")
local roblox = require("@lune/roblox")

local stageDir, outDir = process.args[1], process.args[2]
assert(stageDir and outDir, "usage: convert.luau <stage dir> <out dir>")

local R15 = {
	"Head", "UpperTorso", "LowerTorso",
	"LeftUpperArm", "LeftLowerArm", "LeftHand", "RightUpperArm", "RightLowerArm", "RightHand",
	"LeftUpperLeg", "LeftLowerLeg", "LeftFoot", "RightUpperLeg", "RightLowerLeg", "RightFoot",
}

local function check(model, id)
	local problems = {}
	for _, partName in R15 do
		local part = model:FindFirstChild(partName)
		if not part or not part:IsA("BasePart") then
			table.insert(problems, "missing " .. partName)
		elseif partName ~= "HumanoidRootPart" then
			local motor = part:FindFirstChildOfClass("Motor6D")
			if not motor or not motor.Part0 or not motor.Part1 then
				table.insert(problems, partName .. " has no wired Motor6D")
			end
		end
	end
	local hrp = model:FindFirstChild("HumanoidRootPart")
	if not hrp then table.insert(problems, "missing HumanoidRootPart") end
	if model.PrimaryPart ~= hrp then table.insert(problems, "PrimaryPart is not HumanoidRootPart") end
	local humanoid = model:FindFirstChildOfClass("Humanoid")
	if not humanoid then
		table.insert(problems, "no Humanoid")
	elseif not humanoid:FindFirstChildOfClass("Animator") then
		table.insert(problems, "no Animator")
	else
		-- Base scale means BodyHeightScale 1 (ScaleTo semantics); width/depth/head may
		-- differ from 1 when that is how the character was authored (Knight is 0.9 wide).
		local height = humanoid:FindFirstChild("BodyHeightScale")
		if height and math.abs(height.Value - 1) > 0.02 then
			table.insert(problems, string.format("BodyHeightScale = %.3g at base scale", height.Value))
		end
	end
	local meshes, accessories = 0, 0
	for _, d in model:GetDescendants() do
		if d:IsA("LuaSourceContainer") then table.insert(problems, "script " .. d.Name) end
		if d:IsA("BasePart") and d.Anchored then table.insert(problems, "anchored " .. d.Name) end
		if d:IsA("MeshPart") then meshes += 1 end
		if d:IsA("Accessory") then
			accessories += 1
			local handle = d:FindFirstChild("Handle")
			if not handle or not handle:FindFirstChildOfClass("Weld") then
				table.insert(problems, "accessory not welded: " .. d.Name)
			elseif handle:IsA("MeshPart") and handle:FindFirstChildOfClass("WrapLayer") then
				-- Layered clothing renders at Size / InitialSize; the handle must stay at mesh size.
				if (handle.Size - handle.InitialSize).Magnitude > 1e-3 then
					table.insert(problems, "layered clothing handle resized: " .. d.Name)
				end
			end
		end
	end
	if #problems > 0 then
		error(id .. ": " .. table.concat(problems, "; "))
	end
	return meshes, accessories
end

local count = 0
for _, file in fs.readDir(stageDir) do
	if file:sub(-6) == ".rbxmx" and file ~= "GiantSources.rbxmx" then
		local id = file:sub(1, -7)
		local instances = roblox.deserializeModel(fs.readFile(stageDir .. "/" .. file))
		assert(#instances == 1 and instances[1].ClassName == "Model", id .. ": expected one Model")
		local model = instances[1]
		assert(model.Name == id, id .. ": model is named " .. model.Name)
		local meshes, accessories = check(model, id)
		local out = outDir .. "/" .. id .. ".rbxm"
		fs.writeFile(out, roblox.serializeModel({ model }, false))
		print(string.format("  %-20s %3d mesh parts, %2d accessories → %s (%d KB)", id, meshes, accessories, out:match("[^/\]+$"), #fs.readFile(out) // 1024))
		count += 1
	end
end
print(string.format("converted %d models", count))
