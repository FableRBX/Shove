// Opens a place file in a NEW Roblox Studio instance.
// Usage: node scripts/open-studio.mjs [place.rbxl]   (default: push-a-giant.rbxl)
//
// A Studio that already has the place open keeps showing the copy it loaded;
// a rebuild never reaches it. So every run opens a fresh instance, and any
// window that was already open is an older build.
import { existsSync, readdirSync, statSync } from "node:fs";
import { basename, join, resolve } from "node:path";
import { spawn } from "node:child_process";

const place = resolve(process.argv[2] ?? "push-a-giant.rbxl");
if (!existsSync(place)) {
	console.error(`Place not found: ${place} (run \`npm run assemble\` first)`);
	process.exit(1);
}

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
