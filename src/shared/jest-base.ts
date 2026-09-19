// Specs live beside the code they test, in whichever layer owns it. Jest
// discovers tests per project root, so scripts/run-tests.luau runs one project
// per tree (shared, server, client); each tree's jest.config spreads this base
// and sets its own rootDir.
export const JEST_BASE = {
	testMatch: ["**/*.spec"],
	testTimeout: 10000,
	// Runs before each suite; clears roblox-ts runtime stamps so suites can
	// re-import modules under Jest's per-suite module isolation.
	setupFiles: [script.Parent!.FindFirstChild("jest-setup")],
};
