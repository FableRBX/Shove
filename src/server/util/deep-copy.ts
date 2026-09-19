/**
 * Recursive copy of a plain data table (string/number keys, no userdata), which
 * is exactly what ProfileStore allows in Profile.Data.
 */
export function deepCopy<T>(value: T): T {
	if (!typeIs(value, "table")) return value;

	const copy: Record<string | number, unknown> = {};
	for (const [key, child] of pairs(value as Record<string | number, unknown>)) {
		copy[key] = deepCopy(child);
	}
	return copy as T;
}
