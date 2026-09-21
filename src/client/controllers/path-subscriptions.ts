import type { DataChange, DataPath } from "./player-data-store";

/** True when either path is a prefix of the other. The empty path is a prefix of everything. */
export function pathsOverlap(a: DataPath, b: DataPath): boolean {
	const shared = math.min(a.size(), b.size());
	for (let i = 0; i < shared; i++) {
		if (a[i] !== b[i]) return false;
	}
	return true;
}

interface Subscriber {
	readonly path: DataPath;
	readonly listener: (change: DataChange) => void;
}

/**
 * Subscribers bucketed by the first key of their path, so a change is checked
 * against the root subscribers and one bucket rather than every listener.
 * Arrays, not Sets: dispatch order is subscription order, and Luau's `pairs`
 * would not keep it.
 */
export class PathSubscriptions {
	private readonly root: Subscriber[] = [];
	private readonly buckets = new Map<string | number, Subscriber[]>();

	public subscribe(path: DataPath, listener: (change: DataChange) => void): () => void {
		const subscriber: Subscriber = { path, listener };
		const bucket = this.bucketFor(path);
		bucket.push(subscriber);
		return () => {
			const index = bucket.indexOf(subscriber);
			if (index !== -1) bucket.remove(index);
		};
	}

	/**
	 * Root bucket first, then the change's first-key bucket (every bucket for
	 * an empty path), each filtered by pathsOverlap. A listener that errors is
	 * reported with warn and does not stop the others.
	 */
	public dispatch(change: DataChange): void {
		// A copy, so a listener that unsubscribes during dispatch cannot skip its neighbour.
		const candidates = [...this.root, ...this.candidatesFor(change.path)];
		for (const { path, listener } of candidates) {
			if (!pathsOverlap(path, change.path)) continue;
			const [ok, err] = pcall(listener, change);
			if (!ok) warn(`[push-a-giant] data listener failed at ${change.path.join(".")}: ${tostring(err)}`);
		}
	}

	public count(): number {
		let total = this.root.size();
		for (const [, bucket] of this.buckets) total += bucket.size();
		return total;
	}

	private bucketFor(path: DataPath): Subscriber[] {
		const first = path[0];
		if (first === undefined) return this.root;
		let bucket = this.buckets.get(first);
		if (bucket === undefined) {
			bucket = [];
			this.buckets.set(first, bucket);
		}
		return bucket;
	}

	private candidatesFor(path: DataPath): Subscriber[] {
		const first = path[0];
		if (first !== undefined) return this.buckets.get(first) ?? [];
		const all: Subscriber[] = [];
		for (const [, bucket] of this.buckets) {
			for (const subscriber of bucket) all.push(subscriber);
		}
		return all;
	}
}
