// Opens a place file in a NEW Roblox Studio instance.
// Usage: node scripts/open-studio.mjs [place.rbxl]   (default: push-a-giant.rbxl)
//
// A Studio that already has the place open keeps showing the copy it loaded;
// a rebuild never reaches it. So every run opens a fresh instance, and any
// window that was already open is an older build.
import { copyFileSync, existsSync, readdirSync, statSync, unlinkSync } from "node:fs";
import { basename, dirname, extname, join, resolve } from "node:path";
import { spawn, spawnSync } from "node:child_process";

const source = resolve(process.argv[2] ?? "push-a-giant.rbxl");
if (!existsSync(source)) {
	console.error(`Place not found: ${source} (run \`npm run assemble\` first)`);
	process.exit(1);
}

// Studio titles each window with the path of the place it opened, so a fixed
// name like push-a-giant.rbxl makes every window look the same. Each run opens its
// own copy instead, named <name>-<branch>-<n>.rbxl, so the title bar says which
// feature the window is for. The copy is also what Studio saves back to, so a
// save never lands on the file the next build overwrites.
function currentBranch(dir) {
	const git = (args) => {
		const r = spawnSync("git", args, { cwd: dir, encoding: "utf8" });
		return r.status === 0 ? r.stdout.trim() : "";
	};
	let branch = git(["rev-parse", "--abbrev-ref", "HEAD"]);
	if (branch === "HEAD") branch = git(["rev-parse", "--short", "HEAD"]); // detached
	// Branch names allow "/" and other characters a filename can't carry.
	return branch.replace(/[^A-Za-z0-9._]+/g, "-").replace(/^-+|-+$/g, "") || "nobranch";
}

// What running Studios have open: their command lines (which name the place
// before the window has a title) and their window titles (which follow a Save
// As). Returns null when the process list can't be read, and not knowing must
// never turn into deleting a place someone is working in.
function openStudioPlaces() {
	if (process.platform !== "win32") return null;
	const r = spawnSync(
		"powershell.exe",
		[
			"-NoProfile",
			"-Command",
			"Get-CimInstance Win32_Process -Filter \"Name='RobloxStudioBeta.exe'\" | ForEach-Object { $_.CommandLine; (Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue).MainWindowTitle }",
		],
		{ encoding: "utf8" },
	);
	if (r.error || r.status !== 0) return null;
	return r.stdout.toLowerCase();
}

function branchCopy(source) {
	const dir = dirname(source);
	const ext = extname(source);
	const stem = basename(source, ext);
	const escape = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
	const copies = new RegExp(`^${escape(stem)}-.+-\\d+${escape(ext)}$`, "i");

	// One copy per run would pile up forever, so delete the ones no Studio has
	// open. Studio doesn't lock the file it loaded, so a failed delete can't be
	// the safety net; the process list is.
	const open = openStudioPlaces();
	let removed = 0;
	if (open !== null) {
		for (const file of readdirSync(dir)) {
			const full = join(dir, file);
			if (!copies.test(file) || open.includes(full.toLowerCase())) continue;
			try {
				unlinkSync(full);
				removed++;
			} catch {
				// Held by something we can't see. A stale copy left behind is free.
			}
		}
	}
	if (removed > 0) console.log(`Removed ${removed} old place ${removed === 1 ? "copy" : "copies"} that no Studio has open.`);

	const branch = currentBranch(dir);
	let n = 1;
	while (existsSync(join(dir, `${stem}-${branch}-${n}${ext}`))) n++;
	const copy = join(dir, `${stem}-${branch}-${n}${ext}`);
	copyFileSync(source, copy);
	return copy;
}

const place = branchCopy(source);

// Roblox keeps every version it has ever downloaded under Versions/, and an
// interrupted auto-update leaves a folder with the exe but only part of its
// payload. AppSettings.xml ships with every complete install, so it marks a
// whole one. Newest complete install wins.
function findStudioExe() {
	if (process.platform !== "win32") return undefined;
	const versions = join(process.env.LOCALAPPDATA ?? "", "Roblox", "Versions");
	if (!existsSync(versions)) return undefined;

	return readdirSync(versions)
		.map((name) => join(versions, name))
		.filter((dir) => existsSync(join(dir, "RobloxStudioBeta.exe")) && existsSync(join(dir, "AppSettings.xml")))
		.map((dir) => ({ exe: join(dir, "RobloxStudioBeta.exe"), mtime: statSync(dir).mtimeMs }))
		.sort((a, b) => b.mtime - a.mtime)
		.map((candidate) => candidate.exe)[0];
}

const exe = findStudioExe();

// On macOS, `open` (and the nested RobloxStudio.app, which is only a protocol
// handler) hand Studio a `file://` URL it ignores: it starts on the Start Page
// with "Launch Intent is None". Running the real binary with a plain path opens
// the place, and each run is a new instance.
const macStudioBin = "/Applications/RobloxStudio.app/Contents/MacOS/RobloxStudio";

if (process.platform === "darwin" && existsSync(macStudioBin)) {
	console.log(`Opening ${basename(place)} in a new Studio instance. Windows that were already open hold older builds.`);
	spawn(macStudioBin, [place], { detached: true, stdio: "ignore" }).unref();
} else if (exe === undefined) {
	// Fall back to the OS file association. On Windows that can hand the place
	// to a Studio that is already running instead of starting a new one.
	const opener = process.platform === "darwin" ? "open" : process.platform === "win32" ? "explorer" : "xdg-open";
	console.log(`No Studio install found; opening ${basename(place)} via ${opener}`);
	spawn(opener, [place], { detached: true, stdio: "ignore" }).unref();
} else {
	// Spawn the exe directly: that starts a new instance even when another
	// Studio has this file open, and avoids the shell handler silently no-oping.
	const child = spawn(exe, [place], { detached: true, stdio: "ignore" });
	let exited = false;
	child.on("error", (err) => {
		exited = true;
		console.error(`Could not launch Studio: ${err.message}`);
	});
	child.on("exit", () => {
		exited = true;
	});
	child.unref();

	// An instance that dies on startup (half-extracted install, missing DLL)
	// looks like a healthy detached launch, so give it a moment and check.
	await new Promise((done) => setTimeout(done, 3000));
	if (exited) {
		console.error("Studio exited immediately; no new instance is running.");
		process.exit(1);
	}
	console.log(
		`Opened ${basename(place)} in a new Studio instance (PID ${child.pid}). Windows that were already open hold older builds.`,
	);
}
