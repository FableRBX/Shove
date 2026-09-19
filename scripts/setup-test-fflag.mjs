import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const dir = join(process.env.LOCALAPPDATA, "Roblox", "ClientSettings");
mkdirSync(dir, { recursive: true });

const file = join(dir, "ClientAppSettings.json");
const current = existsSync(file) ? JSON.parse(readFileSync(file, "utf8")) : {};
current.FFlagEnableLoadModule = true;
writeFileSync(file, JSON.stringify(current, null, "\t"));

console.log(`Wrote FFlagEnableLoadModule=true to ${file}`);
