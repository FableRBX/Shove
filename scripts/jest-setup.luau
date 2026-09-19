-- Jest reloads every module per test suite (debug.loadmodule), so each suite
-- gets its own copy of the roblox-ts RuntimeLib. RuntimeLib stamps imported
-- modules into _G to detect duplicate runtimes, which misfires here: the next
-- suite's fresh runtime sees the previous suite's stamps and refuses to import
-- ("Invalid module access!"). Stamps are stale between suites — modules are
-- reloaded fresh anyway — so clear them before each suite runs.
local stale = {}
for key, value in pairs(_G) do
	if typeof(key) == "Instance" and key:IsA("ModuleScript") and type(value) == "table" then
		table.insert(stale, key)
	end
end
for _, key in ipairs(stale) do
	_G[key] = nil
end

return true
