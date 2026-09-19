# anvil Template Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `anvil`, a fork-per-game Roblox template: a roblox-ts + Flamework project that boots to a working empty game with player persistence, replication, intent-based networking, a React UI mount, an in-engine Jest harness, and one deletable example feature (coins).

**Architecture:** Flamework services/controllers over a ProfileStore + Replica data pipeline (server profile → typed mutators → Replica → client controller → React hook). Layer-first at the Rojo boundary (`src/{client,server,shared}`), feature-first within. Pure game logic lives in `shared/` with Jest specs; services stay thin shells.

**Tech Stack:** roblox-ts 3.0, Flamework 1.3 (core/components/networking), ProfileStore, loleris-replica, @rbxts/react 17, Centurion, @rbxts/jest (Jest Lua), Rojo (via Rokit), ESLint 9 flat config + eslint-plugin-roblox-ts 1.4 + Prettier 3.

**Spec:** `docs/superpowers/specs/2026-08-31-anvil-template-design.md`

## Global Constraints

- TypeScript `strict: true`; no `any` (eslint `roblox-ts/no-any` enforces).
- File names are kebab-case. Flamework classes: `@Service`/`@Controller`/`@Component` decorated.
- **Invariant: the client sends intent, the server decides.** Client→server events are named as requested actions.
- **Invariant: profile writes go only through typed mutators on `PlayerDataNode`** (`addCoins`, never a generic `set`).
- All boot logging is prefixed `[anvil]`.
- Dependency versions are exactly those in Task 1's `package.json` — do not substitute.
- `flamework.build` (generated at repo root on first build) IS committed; `out/`, `include/`, `*.rbxl`, `sourcemap.json` are NOT.
- The working directory is `C:\Users\mcbra\dev\roblox\anvil` (git repo already initialized, contains only `docs/`).
- Commands run in PowerShell unless marked otherwise; all listed commands work in both PowerShell 7 and Git Bash.
- Tasks 4, 5, 7, 8 end with a **Human checkpoint**: the user presses Play in Studio and confirms observed behavior. Do not claim those behaviors verified without the user's confirmation.

---

### Task 1: Scaffold and Flamework boot skeleton

**Files:**
- Create: `.gitignore`, `.gitattributes`, `.prettierrc`, `.prettierignore`, `eslint.config.mjs`, `package.json`, `tsconfig.json`, `default.project.json`
- Create: `src/server/runtime.server.ts`, `src/client/runtime.client.ts`
- Create: `src/shared/network.ts`, `src/client/network.ts`, `src/server/network.ts`
- Create (empty, with `.gitkeep`): `src/server/services/`, `src/server/features/`, `src/client/controllers/`, `src/client/features/`, `src/shared/types/`, `src/shared/features/`
- Create (via rokit): `rokit.toml`

**Interfaces:**
- Produces: `GlobalEvents`/`GlobalFunctions` (shared), `Events`/`Functions` (client + server handles), a compiling project and a buildable `anvil.rbxl`. Later tasks add interface members to `shared/network.ts` and files under the `services`/`controllers`/`features` folders, which are already on Flamework's `addPaths` list.

- [x] **Step 1: Pin tools with Rokit**

```powershell
rokit init
rokit add rojo-rbx/rojo@7.7.0
rokit add rojo-rbx/run-in-roblox
rokit add lune-org/lune
rokit install
```

If `rokit add` prompts for trust, run `rokit trust rojo-rbx/rojo rojo-rbx/run-in-roblox lune-org/lune` and retry. Verify: `rojo --version` prints 7.7.0.

- [x] **Step 2: Write `package.json`**

```json
{
	"name": "anvil",
	"version": "0.1.0",
	"description": "Fork-per-game Roblox template built with roblox-ts and Flamework",
	"scripts": {
		"build": "rbxtsc",
		"watch": "rbxtsc -w",
		"assemble": "rbxtsc && rojo build default.project.json -o anvil.rbxl",
		"lint": "eslint src",
		"test": "rbxtsc && rojo build test.project.json -o test.rbxl && run-in-roblox --place test.rbxl --script scripts/run-tests.luau",
		"test:setup": "node scripts/setup-test-fflag.mjs"
	},
	"license": "UNLICENSED",
	"dependencies": {
		"@flamework/components": "^1.3.2",
		"@flamework/core": "^1.3.2",
		"@flamework/networking": "^1.3.2",
		"@rbxts/centurion": "^1.0.1",
		"@rbxts/centurion-ui": "^1.0.8",
		"@rbxts/jest": "3.16.0-ts.1",
		"@rbxts/jest-globals": "3.16.0-ts.1",
		"@rbxts/loleris-replica": "^0.2.0",
		"@rbxts/profile-store": "^1.0.3",
		"@rbxts/react": "17.3.7-ts.2",
		"@rbxts/react-roblox": "17.3.7-ts.2",
		"@rbxts/services": "^1.6.0",
		"@rbxts/signal": "^1.1.1"
	},
	"devDependencies": {
		"@rbxts/compiler-types": "3.0.0-types.0",
		"@rbxts/types": "^1.0.946",
		"eslint": "^9.0.0",
		"eslint-config-prettier": "^10.1.8",
		"eslint-plugin-roblox-ts": "^1.4.1",
		"prettier": "^3.9.6",
		"rbxts-transformer-flamework": "^1.3.2",
		"roblox-ts": "3.0.0",
		"typescript": "^5.5.3",
		"typescript-eslint": "^8.69.0"
	}
}
```

Run `npm install`. If `rbxtsc` later reports a TypeScript version incompatibility, pin `typescript` to the exact version rbxtsc names and re-run `npm install`.

- [x] **Step 3: Write `tsconfig.json`**

```json
{
	"compilerOptions": {
		"allowSyntheticDefaultImports": true,
		"downlevelIteration": true,
		"jsx": "react",
		"jsxFactory": "React.createElement",
		"jsxFragmentFactory": "React.Fragment",
		"module": "commonjs",
		"moduleResolution": "Node",
		"noLib": true,
		"resolveJsonModule": true,
		"forceConsistentCasingInFileNames": true,
		"moduleDetection": "force",
		"strict": true,
		"target": "ESNext",
		"typeRoots": ["node_modules/@rbxts", "node_modules/@flamework"],
		"rootDir": "src",
		"outDir": "out",
		"baseUrl": "src",
		"incremental": true,
		"tsBuildInfoFile": "out/tsconfig.tsbuildinfo",
		"experimentalDecorators": true,
		"plugins": [{ "transform": "rbxts-transformer-flamework", "obfuscation": false }]
	},
	"include": ["src"]
}
```

- [x] **Step 4: Write git and formatter config**

`.gitignore`:

```
/node_modules
/out
/include
*.rbxl
*.rbxl.lock
/sourcemap.json
```

`.gitattributes`:

```
* text=auto
*.rbxl binary
*.rbxm binary
*.rbxmx binary
```

`.prettierrc`:

```json
{
	"useTabs": true,
	"printWidth": 120,
	"trailingComma": "all"
}
```

`.prettierignore`:

```
node_modules
out
include
```

- [x] **Step 5: Write `eslint.config.mjs`**

```js
import tseslint from "typescript-eslint";
import roblox from "eslint-plugin-roblox-ts";
import prettier from "eslint-config-prettier";

export default tseslint.config(
	{ ignores: ["out/**", "include/**", "node_modules/**", "scripts/**", "eslint.config.mjs"] },
	...tseslint.configs.recommended,
	roblox.configs.recommended,
	prettier,
	{
		languageOptions: {
			parserOptions: {
				projectService: true,
				tsconfigRootDir: import.meta.dirname,
			},
		},
		rules: {
			// The template deliberately ships empty, growing interfaces
			// (network event maps, component attribute maps).
			"@typescript-eslint/no-empty-object-type": "off",
		},
	},
);
```

- [x] **Step 6: Write `default.project.json`**

```json
{
	"name": "anvil",
	"globIgnorePaths": ["**/package.json", "**/tsconfig.json"],
	"tree": {
		"$className": "DataModel",
		"ServerScriptService": {
			"$className": "ServerScriptService",
			"TS": { "$path": "out/server" }
		},
		"ReplicatedStorage": {
			"$className": "ReplicatedStorage",
			"rbxts_include": {
				"$path": "include",
				"node_modules": {
					"$className": "Folder",
					"@rbxts": { "$path": "node_modules/@rbxts" },
					"@rbxts-js": { "$path": "node_modules/@rbxts-js" },
					"@flamework": { "$path": "node_modules/@flamework" }
				}
			},
			"TS": { "$path": "out/shared" }
		},
		"StarterPlayer": {
			"$className": "StarterPlayer",
			"StarterPlayerScripts": {
				"$className": "StarterPlayerScripts",
				"TS": { "$path": "out/client" }
			}
		},
		"Workspace": {
			"$properties": {
				"FilteringEnabled": true,
				"StreamingEnabled": true
			},
			"Baseplate": {
				"$className": "Part",
				"$properties": {
					"Anchored": true,
					"Size": [512, 16, 512],
					"Position": [0, -8, 0],
					"Color": [0.38, 0.37, 0.39]
				}
			},
			"SpawnLocation": {
				"$className": "SpawnLocation",
				"$properties": {
					"Anchored": true,
					"Size": [12, 1, 12],
					"Position": [0, 0.5, 0]
				}
			}
		},
		"SoundService": {
			"$className": "SoundService",
			"$properties": { "RespectFilteringEnabled": true }
		},
		"TextChatService": {
			"$properties": { "ChatVersion": "TextChatService" }
		}
	}
}
```

- [x] **Step 7: Write the runtime and network skeleton**

`src/shared/network.ts`:

```ts
import { Networking } from "@flamework/networking";

interface ClientToServerEvents {}

interface ServerToClientEvents {}

interface ClientToServerFunctions {}

interface ServerToClientFunctions {}

export const GlobalEvents = Networking.createEvent<ClientToServerEvents, ServerToClientEvents>();
export const GlobalFunctions = Networking.createFunction<ClientToServerFunctions, ServerToClientFunctions>();
```

`src/client/network.ts`:

```ts
import { GlobalEvents, GlobalFunctions } from "shared/network";

export const Events = GlobalEvents.createClient({});
export const Functions = GlobalFunctions.createClient({});
```

`src/server/network.ts`:

```ts
import { GlobalEvents, GlobalFunctions } from "shared/network";

export const Events = GlobalEvents.createServer({});
export const Functions = GlobalFunctions.createServer({});
```

`src/server/runtime.server.ts`:

```ts
import { Flamework } from "@flamework/core";

Flamework.addPaths("src/server/services");
Flamework.addPaths("src/server/features");

Flamework.ignite();

print("[anvil] server ignited");
```

`src/client/runtime.client.ts`:

```ts
import { Flamework } from "@flamework/core";

Flamework.addPaths("src/client/controllers");
Flamework.addPaths("src/client/features");

Flamework.ignite();

print("[anvil] client ignited");
```

Create the empty folders, each containing an empty `.gitkeep` file: `src/server/services`, `src/server/features`, `src/client/controllers`, `src/client/features`, `src/shared/types`, `src/shared/features`.

- [x] **Step 8: Verify the build**

```powershell
npm run build
npm run lint
npm run assemble
```

Expected: `rbxtsc` exits 0; eslint reports no errors; `anvil.rbxl` exists. If any other lint rule fires on generated-pattern code, suppress per-line with `// eslint-disable-next-line` — do not disable further rules globally.

- [x] **Step 9: Commit**

```powershell
git add -A
git commit -m "Scaffold roblox-ts + Flamework project skeleton"
```

---

### Task 2: In-engine Jest test harness

> **Deviation (2026-09-01):** Executed after Tasks 3–7 (was deferred by user decision). With a second spec file present, Jest Lua's per-suite module isolation trips RuntimeLib's duplicate-runtime guard (`Invalid module access!`): each suite reloads modules via `debug.loadmodule` with a fresh RuntimeLib copy, but RuntimeLib stamps imported modules into the shared `_G`. Fixed by adding `scripts/jest-setup.luau` (clears stale stamps before each suite), wired via `setupFiles` in `jest.config.ts` and mounted as a sibling of `jest.config` in `test.project.json`. The deferred specs from Tasks 3 and 6 landed with this task; final state 3 suites / 7 tests green.

**Files:**
- Create: `test.project.json`, `scripts/run-tests.luau`, `scripts/setup-test-fflag.mjs`
- Create: `src/shared/jest.config.ts`, `src/shared/sanity.spec.ts`

**Interfaces:**
- Consumes: the Task 1 scaffold (`npm test` script already present in `package.json`).
- Produces: a green `npm test` pipeline. Later tasks add `*.spec.ts` files anywhere under `src/shared/` and they are discovered automatically.

- [x] **Step 1: Write `test.project.json`**

A minimal place: shared code + packages only — no server/client scripts, so no Flamework ignition and no ProfileStore sessions during tests.

```json
{
	"name": "anvil-test",
	"globIgnorePaths": ["**/package.json", "**/tsconfig.json"],
	"tree": {
		"$className": "DataModel",
		"ReplicatedStorage": {
			"$className": "ReplicatedStorage",
			"rbxts_include": {
				"$path": "include",
				"node_modules": {
					"$className": "Folder",
					"@rbxts": { "$path": "node_modules/@rbxts" },
					"@rbxts-js": { "$path": "node_modules/@rbxts-js" },
					"@flamework": { "$path": "node_modules/@flamework" }
				}
			},
			"TS": { "$path": "out/shared" }
		}
	}
}
```

- [x] **Step 2: Write `src/shared/jest.config.ts`** (amended: adds `setupFiles` per the deviation note)

```ts
export = {
	testMatch: ["**/*.spec"],
	testTimeout: 10000,
};
```

(Compiles to a ModuleScript named `jest.config` at the root of `ReplicatedStorage.TS`, which Jest Lua requires.)

- [x] **Step 3: Write `src/shared/sanity.spec.ts`**

```ts
import { describe, expect, it } from "@rbxts/jest-globals";

describe("test harness", () => {
	it("runs specs in-engine", () => {
		expect(1 + 1).toBe(2);
	});
});
```

- [x] **Step 4: Write `scripts/run-tests.luau`**

```lua
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Jest = require(ReplicatedStorage.rbxts_include.node_modules["@rbxts"].jest.src)

local root = ReplicatedStorage:WaitForChild("TS")

local status, result = Jest.runCLI(root, {
	verbose = true,
	ci = false,
}, { root }):awaitStatus()

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
```

- [x] **Step 5: Write `scripts/setup-test-fflag.mjs`**

Jest Lua 3.x requires the `FFlagEnableLoadModule` Studio fast flag. This writes it into Studio's global `ClientAppSettings.json` (merging with any existing flags):

```js
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const dir = join(process.env.LOCALAPPDATA, "Roblox", "ClientSettings");
mkdirSync(dir, { recursive: true });

const file = join(dir, "ClientAppSettings.json");
const current = existsSync(file) ? JSON.parse(readFileSync(file, "utf8")) : {};
current.FFlagEnableLoadModule = true;
writeFileSync(file, JSON.stringify(current, null, "\t"));

console.log(`Wrote FFlagEnableLoadModule=true to ${file}`);
```

- [x] **Step 6: Run the harness**

```powershell
npm run test:setup
npm test
```

Expected: `test:setup` prints the settings path. `npm test` compiles, builds `test.rbxl`, launches Roblox Studio via run-in-roblox (Studio must be installed and logged in — if a login prompt appears, this is a human checkpoint), and prints a Jest summary with `1 passed`. Exit code 0.

If the run hangs or Jest errors with a `debug.loadmodule` message, confirm the fast flag file from Step 5 exists, then restart Studio and re-run.

- [x] **Step 7: Commit**

```powershell
git add -A
git commit -m "Add in-engine Jest test harness"
```

---

### Task 3: PlayerData schema and migrations (TDD)

> **Deviation (2026-08-31):** Task 2 (test harness) deferred by user decision. Schema and migrations implemented without their spec files; the TDD steps below land when Task 2 does.

**Files:**
- Create: `src/shared/types/player-data.ts`, `src/shared/types/migrations.ts`
- Test: `src/shared/types/migrations.spec.ts`

**Interfaces:**
- Produces (used by Tasks 4–8):
  - `PLAYER_DATA_TOKEN: string`
  - `interface PlayerData { Version: number; Coins: number; Settings: { [key: string]: boolean } }`
  - `DEFAULT_PLAYER_DATA: PlayerData`
  - `LATEST_VERSION: number`
  - `migrate(data: PlayerData): void` — mutates `data` in place, upgrading `Version` to `LATEST_VERSION`; throws if a step is missing; leaves future-version profiles untouched.

- [x] **Step 1: Write `src/shared/types/player-data.ts`** (the spec file imports it, so it must exist first; `migrate` is what stays unimplemented until Step 4)

```ts
import { LATEST_VERSION } from "./migrations";

export const PLAYER_DATA_TOKEN = "PlayerData";

export interface PlayerData {
	Version: number;
	Coins: number;
	Settings: { [key: string]: boolean };
}

export const DEFAULT_PLAYER_DATA: PlayerData = {
	Version: LATEST_VERSION,
	Coins: 0,
	Settings: {},
};
```

And a stub `src/shared/types/migrations.ts` so the project compiles:

```ts
export const LATEST_VERSION = 1;
```

- [x] **Step 2: Write the failing spec `src/shared/types/migrations.spec.ts`** (landed 2026-09-01 with Task 2)

```ts
import { describe, expect, it } from "@rbxts/jest-globals";
import { DEFAULT_PLAYER_DATA } from "./player-data";
import { LATEST_VERSION, migrate } from "./migrations";

describe("migrate", () => {
	it("leaves a current-version profile untouched", () => {
		const data = { ...DEFAULT_PLAYER_DATA, Settings: { ...DEFAULT_PLAYER_DATA.Settings } };
		migrate(data);
		expect(data.Version).toBe(LATEST_VERSION);
		expect(data.Coins).toBe(DEFAULT_PLAYER_DATA.Coins);
	});

	it("leaves a future-version profile untouched", () => {
		const data = { ...DEFAULT_PLAYER_DATA, Version: LATEST_VERSION + 1 };
		migrate(data);
		expect(data.Version).toBe(LATEST_VERSION + 1);
	});

	it("throws when a migration step is missing", () => {
		const data = { ...DEFAULT_PLAYER_DATA, Version: 0 };
		expect(() => migrate(data)).toThrow();
	});
});
```

- [x] **Step 3: Run tests to verify failure** — skipped: implementation predates the spec (per this task's deviation), so the spec went straight to green.

Run: `npm test`
Expected: FAIL — `migrate` is not exported from `migrations` (compile error from rbxtsc counts as the failing state; the run stops at the compile step).

- [x] **Step 4: Implement `src/shared/types/migrations.ts`**

```ts
import type { PlayerData } from "./player-data";

export const LATEST_VERSION = 1;

/**
 * Each entry upgrades a profile from its key's version to key + 1.
 * When changing the shape of PlayerData: bump LATEST_VERSION, add a step here.
 * Example step, upgrading version 1 profiles after a hypothetical field rename:
 *   [1]: (data) => { data.Coins = math.max(0, data.Coins); }
 */
const MIGRATIONS: { [fromVersion: number]: (data: PlayerData) => void } = {};

export function migrate(data: PlayerData): void {
	while (data.Version < LATEST_VERSION) {
		const step = MIGRATIONS[data.Version];
		if (step === undefined) {
			error(`[anvil] missing migration from profile version ${data.Version}`);
		}
		step(data);
		data.Version += 1;
	}
}
```

- [x] **Step 5: Run tests to verify pass** (2026-09-01: passed as part of the full 7-test run)

Run: `npm test`
Expected: PASS — 4 tests (1 sanity + 3 migrate), 0 failures.

- [x] **Step 6: Commit**

```powershell
git add -A
git commit -m "Add PlayerData schema and migration runner"
```

---

### Task 4: Player spine — PlayerService, PlayerEntity, PlayerDataNode

**Files:**
- Create: `src/server/services/player/player-entity.ts`
- Create: `src/server/services/player/player-data-node.ts`
- Create: `src/server/services/player/player-service.ts`

**Interfaces:**
- Consumes: `PlayerData`, `DEFAULT_PLAYER_DATA`, `PLAYER_DATA_TOKEN`, `migrate` from Task 3.
- Produces (used by Tasks 7–8):
  - `PLAYER_TAG = "Player"` (CollectionService tag added to each ready Player)
  - `PlayerService` with: `playerReady: Signal<(player: Player, entity: PlayerEntity) => void>`, `playerRemoving: Signal<(player: Player, entity: PlayerEntity) => void>`, `getEntity(player): PlayerEntity | undefined`, `getEntities(): ReadonlyMap<Player, PlayerEntity>`, `getDataNode(player): PlayerDataNode | undefined`
  - `PlayerDataNode` with: `getData(): Readonly<PlayerData>`, `addCoins(amount: number): void`, `setSetting(key: string, value: boolean): void`, `coinsChanged: Signal<(total: number) => void>`, `destroy(): void`
  - `PlayerEntity` with: `player: Player`, `dataNode: PlayerDataNode`, `destroy(): void`

- [x] **Step 1: Write `src/server/services/player/player-entity.ts`**

```ts
import { PlayerDataNode } from "./player-data-node";

export class PlayerEntity {
	public readonly player: Player;
	public readonly dataNode: PlayerDataNode;

	constructor(player: Player, dataNode: PlayerDataNode) {
		this.player = player;
		this.dataNode = dataNode;
	}

	public destroy(): void {
		this.dataNode.destroy();
	}
}
```

- [x] **Step 2: Write `src/server/services/player/player-data-node.ts`**

```ts
import Replica, { ReplicaServer as ReplicaServerType } from "@rbxts/loleris-replica";
import ProfileStore from "@rbxts/profile-store";
import Signal from "@rbxts/signal";
import { PLAYER_DATA_TOKEN } from "shared/types/player-data";
import type { PlayerData } from "shared/types/player-data";

const ReplicaServer = Replica as ReplicaServerType;
const PlayerDataToken = ReplicaServer.Token(PLAYER_DATA_TOKEN);

export class PlayerDataNode {
	public readonly replica;
	public readonly profile: ProfileStore.Profile<PlayerData>;

	// coins feature — remove alongside the coins folders.
	public readonly coinsChanged = new Signal<(total: number) => void>();

	constructor(profile: ProfileStore.Profile<PlayerData>, player: Player) {
		this.profile = profile;

		this.replica = new ReplicaServer<PlayerData, { PlayerId: number }>({
			Token: PlayerDataToken,
			Data: profile.Data,
			Tags: { PlayerId: player.UserId },
		});

		this.replica.Replicate();
	}

	public getData(): Readonly<PlayerData> {
		return this.replica.Data;
	}

	// coins feature — remove alongside the coins folders.
	public addCoins(amount: number): void {
		const total = this.replica.Data.Coins + amount;
		this.replica.Set(["Coins"], total);
		this.coinsChanged.Fire(total);
	}

	public setSetting(key: string, value: boolean): void {
		this.replica.Set(["Settings", key], value);
	}

	public destroy(): void {
		this.coinsChanged.Destroy();
		this.replica.Destroy();
		this.profile.EndSession();
	}
}
```

- [x] **Step 3: Write `src/server/services/player/player-service.ts`**

```ts
import { OnStart, Service } from "@flamework/core";
import ProfileStore from "@rbxts/profile-store";
import Signal from "@rbxts/signal";
import { CollectionService, Players } from "@rbxts/services";
import { DEFAULT_PLAYER_DATA } from "shared/types/player-data";
import type { PlayerData } from "shared/types/player-data";
import { migrate } from "shared/types/migrations";
import { PlayerDataNode } from "./player-data-node";
import { PlayerEntity } from "./player-entity";

export const PLAYER_TAG = "Player";

@Service({})
export class PlayerService implements OnStart {
	private store!: ProfileStore.Store<PlayerData>;
	private entities = new Map<Player, PlayerEntity>();

	public readonly playerReady = new Signal<(player: Player, entity: PlayerEntity) => void>();
	public readonly playerRemoving = new Signal<(player: Player, entity: PlayerEntity) => void>();

	onStart(): void {
		this.store = ProfileStore.New<PlayerData>("PlayerData", DEFAULT_PLAYER_DATA);

		Players.PlayerAdded.Connect((player) => this.onPlayerAdded(player));
		Players.PlayerRemoving.Connect((player) => this.onPlayerRemoving(player));

		for (const player of Players.GetPlayers()) {
			task.spawn(() => this.onPlayerAdded(player));
		}
	}

	private onPlayerAdded(player: Player): void {
		const profile = this.store.StartSessionAsync(`${player.UserId}`);

		if (!player.IsDescendantOf(Players)) {
			profile.EndSession();
			return;
		}

		profile.Reconcile();
		profile.AddUserId(player.UserId);
		migrate(profile.Data);

		profile.OnSessionEnd.Connect(() => {
			player.Kick("Your data has been loaded on another server - please rejoin");
		});

		const dataNode = new PlayerDataNode(profile, player);
		const entity = new PlayerEntity(player, dataNode);
		this.entities.set(player, entity);
		CollectionService.AddTag(player, PLAYER_TAG);
		this.playerReady.Fire(player, entity);
		print(`[anvil] profile loaded for ${player.Name}`);
	}

	private onPlayerRemoving(player: Player): void {
		const entity = this.entities.get(player);
		if (entity) {
			this.playerRemoving.Fire(player, entity);
			entity.destroy();
			this.entities.delete(player);
		}
	}

	public getEntities(): ReadonlyMap<Player, PlayerEntity> {
		return this.entities;
	}

	public getEntity(player: Player): PlayerEntity | undefined {
		return this.entities.get(player);
	}

	public getDataNode(player: Player): PlayerDataNode | undefined {
		return this.entities.get(player)?.dataNode;
	}
}
```

- [x] **Step 4: Verify compile, lint, tests**

```powershell
npm run build
npm run lint
npm test
```

Expected: all green (tests unchanged: 4 passing).

- [x] **Step 5: Human checkpoint — boot in Studio**

Build and open the place (use the rojo-dev-loop skill, or `npm run assemble` then open `anvil.rbxl`). Ask the user to press Play and confirm the output shows, in order: `[anvil] server ignited`, `[anvil] client ignited`, `[anvil] profile loaded for <name>`. In Studio's Play Solo, ProfileStore uses a mock store when API access is off — no DataStore setup needed.

- [x] **Step 6: Commit**

```powershell
git add -A
git commit -m "Add player spine: ProfileStore sessions, Replica data nodes"
```

---

### Task 5: Client data layer and React UI mount

**Files:**
- Create: `src/client/controllers/player-data-controller.ts`
- Create: `src/client/controllers/app-controller.tsx`
- Create: `src/client/ui/app.tsx`
- Create: `src/client/ui/hooks/use-player-data.ts`

**Interfaces:**
- Consumes: `PLAYER_DATA_TOKEN`, `PlayerData` (Task 3).
- Produces (used by Task 7):
  - `PlayerDataController` with `getData(): PlayerData | undefined` and `dataChanged: Signal<(data: PlayerData) => void>` (fires with a fresh object reference on every replica change)
  - `usePlayerData(): PlayerData | undefined` React hook
  - `App` React component (the spine's root ScreenGui shell)

- [x] **Step 1: Write `src/client/controllers/player-data-controller.ts`**

```ts
import { Controller, OnStart } from "@flamework/core";
import Replica, { ReplicaClient as ReplicaClientType } from "@rbxts/loleris-replica";
import Signal from "@rbxts/signal";
import { Players } from "@rbxts/services";
import { PLAYER_DATA_TOKEN } from "shared/types/player-data";
import type { PlayerData } from "shared/types/player-data";

const ReplicaClient = Replica as ReplicaClientType;

@Controller({})
export class PlayerDataController implements OnStart {
	private data?: PlayerData;

	public readonly dataChanged = new Signal<(data: PlayerData) => void>();

	onStart(): void {
		ReplicaClient.OnNew(PLAYER_DATA_TOKEN, (replica) => {
			if (replica.Tags.PlayerId !== Players.LocalPlayer.UserId) return;

			const publish = () => {
				const snapshot = { ...(replica.Data as unknown as PlayerData) };
				this.data = snapshot;
				this.dataChanged.Fire(snapshot);
			};

			replica.OnChange(publish);
			publish();
			print("[anvil] player data replica received");
		});

		ReplicaClient.RequestData();
	}

	public getData(): PlayerData | undefined {
		return this.data;
	}
}
```

- [x] **Step 2: Write `src/client/ui/hooks/use-player-data.ts`**

```ts
import { Dependency } from "@flamework/core";
import { useEffect, useState } from "@rbxts/react";
import { PlayerDataController } from "client/controllers/player-data-controller";
import type { PlayerData } from "shared/types/player-data";

export function usePlayerData(): PlayerData | undefined {
	const [data, setData] = useState<PlayerData | undefined>(undefined);

	useEffect(() => {
		const controller = Dependency<PlayerDataController>();
		const connection = controller.dataChanged.Connect((value) => setData(value));
		setData(controller.getData());
		return () => connection.Disconnect();
	}, []);

	return data;
}
```

- [x] **Step 3: Write `src/client/ui/app.tsx`**

```tsx
import React from "@rbxts/react";

export function App() {
	// Spine shell: mount fork-wide providers and always-on UI here.
	return (
		<screengui
			key="AnvilApp"
			ResetOnSpawn={false}
			IgnoreGuiInset={true}
			ZIndexBehavior={Enum.ZIndexBehavior.Sibling}
		/>
	);
}
```

- [x] **Step 4: Write `src/client/controllers/app-controller.tsx`**

```tsx
import { Controller, OnStart } from "@flamework/core";
import React from "@rbxts/react";
import { createPortal, createRoot } from "@rbxts/react-roblox";
import { Players } from "@rbxts/services";
import { App } from "client/ui/app";

@Controller({})
export class AppController implements OnStart {
	onStart(): void {
		const playerGui = Players.LocalPlayer.WaitForChild("PlayerGui") as PlayerGui;

		// React roots take ownership of their container, so mount into an
		// owned Folder and portal into PlayerGui rather than mounting on it.
		const container = new Instance("Folder");
		container.Name = "App";
		container.Parent = playerGui;

		const root = createRoot(container);
		root.render(createPortal(<App />, playerGui));
	}
}
```

- [x] **Step 5: Verify compile, lint, tests**

```powershell
npm run build
npm run lint
npm test
```

Expected: all green.

- [x] **Step 6: Human checkpoint — Studio**

Rebuild and open the place. Ask the user to press Play and confirm: output shows `[anvil] player data replica received`, and the Explorer under `Players.<name>.PlayerGui` contains a `AnvilApp` ScreenGui.

- [x] **Step 7: Commit**

```powershell
git add -A
git commit -m "Add client data controller and React UI mount"
```

---

### Task 6: Coins pure logic (TDD)

> **Deviation (2026-08-31):** Test harness still deferred — logic implemented without its spec file; the spec lands with Task 2.

**Files:**
- Create: `src/shared/features/coins/coins-config.ts`, `src/shared/features/coins/can-request-coin.ts`
- Test: `src/shared/features/coins/can-request-coin.spec.ts`

**Interfaces:**
- Produces (used by Task 7):
  - `COIN_REQUEST_COOLDOWN: number` (seconds, value `1`)
  - `canRequestCoin(lastRequestAt: number | undefined, now: number, cooldown: number): boolean`

- [x] **Step 1: Write the failing spec `src/shared/features/coins/can-request-coin.spec.ts`** (landed 2026-09-01 with Task 2)

```ts
import { describe, expect, it } from "@rbxts/jest-globals";
import { canRequestCoin } from "./can-request-coin";

describe("canRequestCoin", () => {
	it("allows the first request", () => {
		expect(canRequestCoin(undefined, 100, 1)).toBe(true);
	});

	it("blocks a request inside the cooldown", () => {
		expect(canRequestCoin(100, 100.5, 1)).toBe(false);
	});

	it("allows a request after the cooldown", () => {
		expect(canRequestCoin(100, 101, 1)).toBe(true);
	});
});
```

- [x] **Step 2: Run tests to verify failure** — skipped: implementation predates the spec (per this task's deviation), so the spec went straight to green.

Run: `npm test`
Expected: FAIL at the compile step — `can-request-coin` module does not exist.

- [x] **Step 3: Implement**

`src/shared/features/coins/coins-config.ts`:

```ts
export const COIN_REQUEST_COOLDOWN = 1;
```

`src/shared/features/coins/can-request-coin.ts`:

```ts
export function canRequestCoin(lastRequestAt: number | undefined, now: number, cooldown: number): boolean {
	if (lastRequestAt === undefined) return true;
	return now - lastRequestAt >= cooldown;
}
```

- [x] **Step 4: Run tests to verify pass** (2026-09-01: passed as part of the full 7-test run)

Run: `npm test`
Expected: PASS — 7 tests total, 0 failures.

- [x] **Step 5: Commit**

```powershell
git add -A
git commit -m "Add coins request cooldown logic"
```

---

### Task 7: Coins vertical slice — network, server, leaderstats, HUD

> **Amendment (2026-08-31, user review):** leaderstats folder ownership moved to a new spine service `src/server/services/leaderstats-service.ts` (`addStat(player, name, initial): IntValue`, folder created lazily) — several features will contribute stats, so no single feature may own the folder. `coins-leaderstats.ts` consumes it via DI.

**Files:**
- Modify: `src/shared/network.ts` (add `requestCoin` to `ClientToServerEvents`)
- Create: `src/server/features/coins/coins-service.ts`
- Create: `src/server/features/coins/coins-leaderstats.ts`
- Create: `src/client/features/coins/coins-hud.tsx`
- Create: `src/client/features/coins/coins-hud-controller.tsx`

**Interfaces:**
- Consumes: `PlayerService`, `PLAYER_TAG`, `PlayerDataNode.addCoins`/`coinsChanged` (Task 4); `usePlayerData` (Task 5); `canRequestCoin`, `COIN_REQUEST_COOLDOWN` (Task 6); `Events` client/server handles (Task 1).
- Produces: the complete example feature. Deleting the coins feature from a fork means deleting `src/{client,server,shared}/features/coins/`, the `Coins` field in `player-data.ts`, the `addCoins`/`coinsChanged` members in `player-data-node.ts`, `requestCoin` in `network.ts`, and (after Task 8) the `givecoins` admin command — nothing else. Task 10's drill proves this.

- [x] **Step 1: Add the intent to `src/shared/network.ts`**

Replace the `ClientToServerEvents` interface with:

```ts
interface ClientToServerEvents {
	// coins feature: ask the server for one coin. The server decides.
	requestCoin(): void;
}
```

- [x] **Step 2: Write `src/server/features/coins/coins-service.ts`**

```ts
import { OnStart, Service } from "@flamework/core";
import { Events } from "server/network";
import { PlayerService } from "server/services/player/player-service";
import { canRequestCoin } from "shared/features/coins/can-request-coin";
import { COIN_REQUEST_COOLDOWN } from "shared/features/coins/coins-config";

@Service({})
export class CoinsService implements OnStart {
	private lastRequestAt = new Map<Player, number>();

	constructor(private readonly playerService: PlayerService) {}

	onStart(): void {
		Events.requestCoin.connect((player) => this.onRequestCoin(player));
		this.playerService.playerRemoving.Connect((player) => this.lastRequestAt.delete(player));
	}

	private onRequestCoin(player: Player): void {
		const now = os.clock();
		if (!canRequestCoin(this.lastRequestAt.get(player), now, COIN_REQUEST_COOLDOWN)) return;

		const dataNode = this.playerService.getDataNode(player);
		if (dataNode === undefined) return;

		this.lastRequestAt.set(player, now);
		dataNode.addCoins(1);
	}
}
```

- [x] **Step 3: Write `src/server/features/coins/coins-leaderstats.ts`**

```ts
import { BaseComponent, Component } from "@flamework/components";
import { OnStart } from "@flamework/core";
import { PLAYER_TAG, PlayerService } from "server/services/player/player-service";

@Component({ tag: PLAYER_TAG })
export class CoinsLeaderstats extends BaseComponent<{}, Player> implements OnStart {
	private connection?: RBXScriptConnection;

	constructor(private readonly playerService: PlayerService) {
		super();
	}

	onStart(): void {
		const dataNode = this.playerService.getDataNode(this.instance);
		if (dataNode === undefined) return;

		const leaderstats = new Instance("Folder");
		leaderstats.Name = "leaderstats";

		const coins = new Instance("IntValue");
		coins.Name = "Coins";
		coins.Value = dataNode.getData().Coins;
		coins.Parent = leaderstats;

		leaderstats.Parent = this.instance;

		this.connection = dataNode.coinsChanged.Connect((total) => {
			coins.Value = total;
		});
	}

	override destroy(): void {
		this.connection?.Disconnect();
		super.destroy();
	}
}
```

- [x] **Step 4: Write `src/client/features/coins/coins-hud.tsx`**

```tsx
import React, { useCallback } from "@rbxts/react";
import { Events } from "client/network";
import { usePlayerData } from "client/ui/hooks/use-player-data";

export function CoinsHud() {
	const data = usePlayerData();

	const onRequestCoin = useCallback(() => {
		Events.requestCoin.fire();
	}, []);

	if (data === undefined) return <></>;

	return (
		<frame
			key="CoinsPanel"
			AnchorPoint={new Vector2(0.5, 0)}
			Position={UDim2.fromScale(0.5, 0.02)}
			Size={UDim2.fromOffset(220, 90)}
			BackgroundColor3={Color3.fromRGB(30, 30, 30)}
			BackgroundTransparency={0.2}
		>
			<uicorner CornerRadius={new UDim(0, 8)} />
			<uilistlayout
				SortOrder={Enum.SortOrder.LayoutOrder}
				Padding={new UDim(0, 6)}
				HorizontalAlignment={Enum.HorizontalAlignment.Center}
				VerticalAlignment={Enum.VerticalAlignment.Center}
			/>
			<textlabel
				key="Count"
				LayoutOrder={1}
				Text={`Coins: ${data.Coins}`}
				TextColor3={new Color3(1, 1, 1)}
				TextSize={20}
				BackgroundTransparency={1}
				Size={UDim2.fromOffset(200, 28)}
			/>
			<textbutton
				key="GetCoin"
				LayoutOrder={2}
				Text="Get Coin"
				TextSize={18}
				TextColor3={new Color3(1, 1, 1)}
				BackgroundColor3={Color3.fromRGB(0, 120, 215)}
				Size={UDim2.fromOffset(120, 32)}
				Event={{ Activated: onRequestCoin }}
			>
				<uicorner CornerRadius={new UDim(0, 6)} />
			</textbutton>
		</frame>
	);
}
```

- [x] **Step 5: Write `src/client/features/coins/coins-hud-controller.tsx`**

Features mount their own UI so deleting the feature deletes its interface:

```tsx
import { Controller, OnStart } from "@flamework/core";
import React from "@rbxts/react";
import { createPortal, createRoot } from "@rbxts/react-roblox";
import { Players } from "@rbxts/services";
import { CoinsHud } from "./coins-hud";

@Controller({})
export class CoinsHudController implements OnStart {
	onStart(): void {
		const playerGui = Players.LocalPlayer.WaitForChild("PlayerGui") as PlayerGui;

		const container = new Instance("Folder");
		container.Name = "CoinsHud";
		container.Parent = playerGui;

		const root = createRoot(container);
		root.render(
			createPortal(
				<screengui key="CoinsHud" ResetOnSpawn={false}>
					<CoinsHud />
				</screengui>,
				playerGui,
			),
		);
	}
}
```

- [x] **Step 6: Verify compile, lint, tests**

```powershell
npm run build
npm run lint
npm test
```

Expected: all green (7 tests).

- [x] **Step 7: Human checkpoint — Studio**

Rebuild and open the place. Ask the user to press Play and confirm: the HUD shows `Coins: 0`; clicking **Get Coin** increments it; spam-clicking is limited to ~1 coin/second; the player list leaderstats column shows `Coins` matching the HUD; stopping and re-Playing keeps the count (mock ProfileStore persists within the session only, so a fresh Studio session resetting to the persisted DataStore value — or 0 in mock mode — is expected).

- [x] **Step 8: Commit**

```powershell
git add -A
git commit -m "Add coins example feature: intent, service, leaderstats, HUD"
```

---

### Task 8: Centurion dev commands

**Files:**
- Create: `src/client/centurion.client.ts`
- Create: `src/server/centurion.server.ts`
- Create: `src/server/commands/admin.ts`

**Interfaces:**
- Consumes: `PlayerService` (Task 4), `PlayerDataNode.addCoins` (Task 4).
- Produces: an in-game command console (activation key F2) with `givecoins` and `viewdata` commands, gated to Studio and an admin allowlist.

- [x] **Step 1: Write `src/client/centurion.client.ts`**

```ts
import { Centurion } from "@rbxts/centurion";
import { CenturionUI } from "@rbxts/centurion-ui";

const client = Centurion.client();
client
	.start()
	.then(() => {
		CenturionUI.start(client, { activationKeys: [Enum.KeyCode.F2] });
	})
	.catch((err) => warn("[anvil] Centurion client failed to start:", err));
```

- [x] **Step 2: Write `src/server/centurion.server.ts`**

```ts
import { Centurion } from "@rbxts/centurion";

const server = Centurion.server();
server.registry.load(script.Parent!.FindFirstChild("commands")!);
server.start();
```

- [x] **Step 3: Write `src/server/commands/admin.ts`** (amended: eslint-disable for the decorator-registered class; `givecoins` marked with the coins-feature removal comment)

```ts
import { Dependency } from "@flamework/core";
import { CenturionType, Command, CommandContext, CommandGuard, Guard, Register } from "@rbxts/centurion";
import { RunService } from "@rbxts/services";
import { PlayerService } from "server/services/player/player-service";

const ADMIN_IDS = new Set<number>([418255008]);

const isAdmin: CommandGuard = (ctx) => {
	if (!RunService.IsStudio() && !ADMIN_IDS.has(ctx.executor.UserId)) {
		ctx.error("Insufficient permission!");
		return false;
	}
	return true;
};

function formatValue(lines: string[], value: unknown, depth: number): void {
	const indent = "  ".rep(depth);
	if (typeIs(value, "table")) {
		for (const [k, v] of pairs(value as Record<string, unknown>)) {
			if (typeIs(v, "table")) {
				lines.push(`${indent}${k}:`);
				formatValue(lines, v, depth + 1);
			} else {
				lines.push(`${indent}${k}: ${tostring(v)}`);
			}
		}
	} else {
		lines.push(`${indent}${tostring(value)}`);
	}
}

@Register()
@Guard(isAdmin)
class AdminCommands {
	@Command({
		name: "viewdata",
		description: "View a player's data",
		arguments: [{ name: "player", description: "The target player", type: CenturionType.Player }],
	})
	viewData(ctx: CommandContext, player: Player) {
		const playerService = Dependency<PlayerService>();
		const dataNode = playerService.getDataNode(player);

		if (!dataNode) {
			ctx.error(`Player data not found for ${player.Name}`);
			return;
		}

		const lines: string[] = [`--- ${player.Name} ---`];
		formatValue(lines, dataNode.getData(), 0);
		ctx.reply(lines.join("\n"));
	}

	@Command({
		name: "givecoins",
		description: "Give coins to a player",
		arguments: [
			{ name: "player", description: "The target player", type: CenturionType.Player },
			{ name: "amount", description: "Number of coins", type: CenturionType.Number },
		],
	})
	giveCoins(ctx: CommandContext, player: Player, amount: number) {
		const playerService = Dependency<PlayerService>();
		const dataNode = playerService.getDataNode(player);

		if (!dataNode) {
			ctx.error(`Player data not found for ${player.Name}`);
			return;
		}

		dataNode.addCoins(amount);
		ctx.reply(`Gave ${amount} coins to ${player.Name}`);
	}
}
```

- [x] **Step 4: Verify compile, lint, tests**

```powershell
npm run build
npm run lint
npm test
```

Expected: all green. Note: `admin.ts` is loaded by Centurion's registry (`centurion.server.ts`), not by Flamework `addPaths` — no runtime path registration needed.

- [x] **Step 5: Human checkpoint — Studio** (verified 2026-09-01: F2 console opens, `givecoins` bumps HUD + leaderstats, `viewdata` renders the profile dump. Note: closing the console is click-outside or Esc-then-F2 — the text field captures focus, so F2 alone is swallowed while typing.)

Rebuild and open the place. Ask the user to press Play, press **F2**, run `givecoins <their name> 50`, and confirm the HUD and leaderstats jump by 50; then run `viewdata <their name>` and confirm the data dump renders.

- [x] **Step 6: Commit**

```powershell
git add -A
git commit -m "Add Centurion dev command console with admin commands"
```

---

### Task 9: Documentation — CLAUDE.md, CONTEXT.md, README, ADRs

**Files:**
- Create: `CLAUDE.md`, `CONTEXT.md`, `README.md`
- Create: `docs/adr/README.md`, `docs/adr/0001-flamework-over-hand-rolled-loader.md`, `docs/adr/0002-profilestore-and-replica.md`, `docs/adr/0003-react-for-ui.md`, `docs/adr/0004-in-engine-jest.md`, `docs/adr/0005-template-repo-over-packages.md`

**Interfaces:**
- Consumes: everything built in Tasks 1–8 (the docs describe it).
- Produces: the fork-facing documentation contract.

- [x] **Step 1: Write `CLAUDE.md`**

````markdown
# anvil

A fork-per-game Roblox template built with roblox-ts and Flamework. Every game
starts as a fork of this repo, so the spine is permanent: a mistake here cannot
be un-shipped from games already forked. Invariants outrank features.

## Invariants

- **The client sends intent; the server decides.** Client→server events are
  named as requested actions (`requestCoin`), never resulting states. Handlers
  validate game rules and silently drop invalid intents.
- **Profile writes go only through typed mutators on `PlayerDataNode`**
  (`addCoins`, never a generic `set`). All other access is
  `getData(): Readonly<PlayerData>`.
- **Services expose behavior and signals, not raw state.** One writer per
  piece of state.
- **Every per-player object owns its connections and instances** and releases
  them in `destroy()`. `PlayerService` guarantees `destroy()` runs exactly once
  per entity on leave.
- **Game logic is a functional core**: pure functions in `src/shared/` with
  `*.spec.ts` beside them; services and controllers stay thin shells.

## Layout

`src/{client,server,shared}` — layer-first at the Rojo boundary, feature-first
within. A **feature** is a deletable unit of gameplay: deleting it means
deleting its three `features/<name>/` folders plus its schema field, mutators,
and network events — and nothing else. The `coins` feature is the living
example of every seam; read it before adding a feature.

## Stack

Flamework (services/controllers/components, DI, typed networking), ProfileStore
(persistence, session locking), loleris-replica (server→client replication),
@rbxts/react (UI, portal-mounted from controllers), Centurion (F2 dev console),
@rbxts/jest (in-engine tests). Decisions live in `docs/adr/`.

## Commands

- `npm run build` / `npm run watch` — compile TS → Luau
- `npm run assemble` — compile + build `anvil.rbxl`
- `npm test` — compile, build test place, run Jest in-engine (one-time machine
  setup: `npm run test:setup`, which writes Studio's `FFlagEnableLoadModule`)
- `npm run lint` — eslint

## Data

Schema in `src/shared/types/player-data.ts`. Additive changes: extend the
interface and `DEFAULT_PLAYER_DATA` (ProfileStore `Reconcile` fills old
profiles). Shape changes: bump `LATEST_VERSION` and add a step in
`src/shared/types/migrations.ts`.
````

- [x] **Step 2: Write `CONTEXT.md`**

````markdown
# anvil

A fork-per-game Roblox template: permanent infrastructure every future game
inherits by forking this repo.

## Language

**Spine**: The permanent infrastructure every fork inherits — lifecycle,
persistence, replication, networking, UI mount, testing.
_Avoid_: framework (that word means Flamework here), engine

**Satellite**: An opt-in package a fork adds for its genre; never required by
the spine.
_Avoid_: plugin, extension

**Service**: A Flamework `@Service` class on the server.

**Controller**: A Flamework `@Controller` class on the client; the Service's
client twin.

**Component**: A Flamework `@Component` class bound to a CollectionService tag.

**Feature**: A deletable unit of gameplay spanning up to all three layers plus
its schema field, mutators, and network events. Deleting a feature is deleting
those and nothing else.

**Profile**: A player's persisted, versioned data document (ProfileStore).
One per player, loaded at join, released at leave.
_Avoid_: save, player data (as a noun)

**Migration**: A pure step upgrading a Profile from one version to the next;
migrations run in sequence at load, before the Replica exists.

**Mutator**: A typed, operation-shaped write method on `PlayerDataNode`
(`addCoins`, not `setCoins`). The only write path; all other access is
read-only.

**Intent**: A client→server event naming a requested action, never a resulting
state. The server decides the outcome.
_Avoid_: command, RPC

**State**: Server-owned data mirrored to clients through Replica. Clients read
it and never write it. Intents travel over Flamework networking; State travels
over Replica — never the reverse.
````

- [x] **Step 3: Write `README.md`**

````markdown
# anvil

A fork-per-game Roblox template built with [roblox-ts](https://roblox-ts.com/)
and [Flamework](https://flamework.fireboltofdeath.dev/). Fork it, rename it,
ship a game; the spine (persistence, replication, networking, UI mount,
testing) comes along.

## Stack

- **roblox-ts** — TypeScript → Luau compiler
- **Flamework** — services/controllers with DI and typed networking
- **ProfileStore** — player data persistence with session locking
- **loleris-replica** — server→client state replication
- **@rbxts/react** — UI (React Lua)
- **Centurion** — dev command console (F2)
- **@rbxts/jest** — in-engine Jest tests

## Getting started

```sh
rokit install         # pins Rojo, run-in-roblox, Lune
npm install
npm run test:setup    # one-time: enables Studio's FFlagEnableLoadModule for Jest
npm run assemble      # compile + build anvil.rbxl
npm test              # run the in-engine test suite
```

Open `anvil.rbxl` in Studio and press Play: you should see `[anvil] server ignited`,
`[anvil] client ignited`, and a coins HUD wired end-to-end (button → intent →
validation → mutator → Replica → React).

## Forking a new game

1. Fork/copy this repo; rename in `package.json`, `default.project.json`,
   `test.project.json`, `README.md`.
2. Keep or delete the example `coins` feature (see `CLAUDE.md` for the
   deletion contract).
3. Build gameplay as features: pure logic in `src/shared/features/<name>/`
   with specs, thin services/controllers beside it.

Conventions and invariants: `CLAUDE.md`. Vocabulary: `CONTEXT.md`.
Decisions: `docs/adr/`.
````

- [x] **Step 4: Write the ADRs** (amended: ADR 0004 also records the Jest per-suite reload / RuntimeLib `_G` stamp workaround from Task 2)

`docs/adr/README.md`:

````markdown
# Architecture Decision Records

Decisions that shape the spine. A decision earns an ADR when reversing it
would touch every fork. Format: context, decision, consequences — one page
maximum. Number sequentially: `NNNN-slug.md`.
````

`docs/adr/0001-flamework-over-hand-rolled-loader.md`:

````markdown
# 0001 — Flamework over a hand-rolled loader

**Context.** The Luau predecessor (`seed`) rejected game frameworks and DI in
favor of a ~100-line loader, valuing transparency over convenience. roblox-ts
changes the calculus: Flamework is the ecosystem's dominant backbone, its DI is
compile-time-generated (no runtime registry or string lookup), and its
networking macros produce runtime type guards for free.

**Decision.** Use Flamework core/components/networking as the spine's
backbone: `@Service`/`@Controller` lifecycle classes, constructor injection,
typed `GlobalEvents`.

**Consequences.** Every fork depends on Flamework and its transformer; the
`flamework.build` id file must be committed. In exchange: no loader to
maintain, DI without magic strings, and validated remotes without hand-written
guards.
````

`docs/adr/0002-profilestore-and-replica.md`:

````markdown
# 0002 — ProfileStore + Replica for persistence and replication

**Context.** The data pipeline needs session-locked persistence and
server→client mirroring. The adjacent `Hatch` project proved
`@rbxts/profile-store` + `@rbxts/loleris-replica` under roblox-ts. The
alternative modern stack (Charm atoms + charm-sync + Lapis) is more idiomatic
TS but unproven in this portfolio.

**Decision.** ProfileStore owns the profile document; each player gets a
`PlayerDataNode` pairing the profile with a Replica created over
`profile.Data`. Mutators write through `replica.Set` so every change
replicates. Clients read via `ReplicaClient.OnNew(token)`.

**Consequences.** Mutable document + path-based writes (not immutable
snapshots); the client controller re-publishes a fresh object per change so
React re-renders. Replication is whole-profile to all clients — switch to
`Subscribe` if a fork needs private data.
````

`docs/adr/0003-react-for-ui.md`:

````markdown
# 0003 — React for UI

**Context.** The spine ships a UI mount. The portfolio's Luau work already
uses React-Lua, and `@rbxts/react` is the maintained roblox-ts binding.

**Decision.** `@rbxts/react` + `@rbxts/react-roblox`. Controllers mount roots
into an owned Folder and portal into PlayerGui (roots take ownership of their
container). Features mount their own ScreenGuis so deleting a feature deletes
its UI. Data reaches components through the `usePlayerData` hook.

**Consequences.** JSX/TSX with `React.createElement` factories in tsconfig;
declarative UI testable by inspection; a second render tree (Roblox instances)
owned entirely by React — never mutate React-owned instances imperatively.
````

`docs/adr/0004-in-engine-jest.md`:

````markdown
# 0004 — In-engine Jest for tests

**Context.** Game logic lands as pure functions in `src/shared/` (functional
core). Those need a runner. Jest Lua runs the real compiled Luau inside the
real engine — no semantic drift between test and production runtimes, unlike
running the TS under Node.

**Decision.** `@rbxts/jest` specs (`*.spec.ts`) colocated with the logic;
`test.project.json` builds a minimal place (shared + packages only, no
Flamework ignition); `run-in-roblox` executes `scripts/run-tests.luau`.

**Consequences.** Tests need Studio installed and the one-time
`FFlagEnableLoadModule` setup (`npm run test:setup`); runs cost seconds, not
milliseconds — so services stay thin and logic stays pure to keep the tested
surface wide and the suite small.
````

`docs/adr/0005-template-repo-over-packages.md`:

````markdown
# 0005 — Template repo over published packages

**Context.** The spine could ship as versioned npm packages that forks depend
on, or as ordinary source files in a template repo.

**Decision.** Template repo. Every game forks it; spine code is ordinary
editable source. Improvements flow forward by forking fresh, or into a live
game via `git merge` from the template remote.

**Consequences.** No publishing/versioning infrastructure to run; forks may
freely patch their spine. The cost: fixes do not propagate automatically —
merging upstream is a deliberate per-game act.
````

- [x] **Step 5: Verify docs render and commit**

Skim each file for broken formatting. Then:

```powershell
git add -A
git commit -m "Add template documentation: invariants, vocabulary, ADRs"
```

---

### Task 10: Final verification and the deletion drill

> **Deviation (2026-09-01):** This task's checkboxes had been checked prematurely in an earlier session; the work actually ran today. The drill caught one real coupling — `migrations.spec.ts` asserted on `DEFAULT_PLAYER_DATA.Coins` — fixed on main per this task's rule (the spec now asserts only on `Version`). The drill's canonical recipe (folders + schema field + data-node members + network event + `givecoins`) then went green: 4 tests, clean build and lint. Separately, branch switching exposed a tooling trap: rbxtsc's incremental cache can skip re-emitting restored files, leaving `out/` incomplete and specs hanging on `WaitForChild` — documented in CLAUDE.md; delete `out/` after switching branches.
- Modify: `docs/superpowers/specs/2026-08-31-anvil-template-design.md` (status line only)

- [x] **Step 1: Full green run**

```powershell
npm run build
npm run lint
npm test
npm run assemble
```

Expected: zero errors everywhere; 7 tests passing; `anvil.rbxl` produced.

- [x] **Step 2: Deletion drill — prove the feature contract**

On a throwaway branch, delete the coins feature exactly per the contract and prove the template stays green:

```powershell
git checkout -b drill/delete-coins
Remove-Item -Recurse -Force src/client/features/coins, src/server/features/coins, src/shared/features/coins
```

Then edit:
- `src/shared/types/player-data.ts`: remove the `Coins` field from `PlayerData` and `DEFAULT_PLAYER_DATA`.
- `src/server/services/player/player-data-node.ts`: remove `coinsChanged` and `addCoins` (and the two "coins feature" comments).
- `src/shared/network.ts`: remove `requestCoin`, leaving the empty interface.
- `src/server/commands/admin.ts`: remove the `giveCoins` command (it calls `addCoins`; `viewdata` stays).

Run:

```powershell
npm run build
npm run lint
npm test
```

Expected: all green (4 tests — sanity + migrate). If anything else had to change to get green, the contract is broken: fix the coupling on `main`, not the drill branch, and re-run the drill.

Note the drill exposes that `givecoins` is coins-coupled; that is accepted and documented by the drill itself (admin commands are expected casualties of deleting the currency they manipulate — the contract's "nothing else" applies to the spine, and the drill edit list above is the canonical deletion recipe).

- [x] **Step 3: Discard the drill**

```powershell
git checkout main
git branch -D drill/delete-coins
```

- [x] **Step 4: Mark the spec implemented**

In `docs/superpowers/specs/2026-08-31-anvil-template-design.md`, change `**Status:** Approved` to `**Status:** Implemented`. Update the deletion-contract wording in the spec's success criteria to match the drill's canonical recipe (folders + schema field + data-node members + network event + coins admin command).

- [x] **Step 5: Commit**

```powershell
git add -A
git commit -m "Verify template end-to-end; document coins deletion drill"
```
