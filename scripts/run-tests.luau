local ReplicatedStorage = game:GetService("ReplicatedStorage")
local ServerScriptService = game:GetService("ServerScriptService")
local StarterPlayer = game:GetService("StarterPlayer")

local Jest = require(ReplicatedStorage.rbxts_include.node_modules["@rbxts"].jest.src)

-- One Jest project per tree: jest-roblox discovers specs by walking each
-- project's rootDir, so every tree that holds specs is its own project.
local shared = ReplicatedStorage:WaitForChild("TS")
local server = ServerScriptService:WaitForChild("TS")
local client = StarterPlayer:WaitForChild("StarterPlayerScripts"):WaitForChild("TS")

local status, result = Jest.runCLI(shared, {
	verbose = true,
	ci = false,
}, { shared, server, client }):awaitStatus()

local ok = status == "Resolved"
	and result.results.numFailedTestSuites == 0
	and result.results.numFailedTests == 0

if status == "Rejected" then
	print(result)
end

local processServiceExists, ProcessService = pcall(function()
	return game:GetService("ProcessService")
end)
if processServiceExists then
	ProcessService:ExitAsync(ok and 0 or 1)
end
