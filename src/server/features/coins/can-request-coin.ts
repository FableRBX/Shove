export function canRequestCoin(lastRequestAt: number | undefined, now: number, cooldown: number): boolean {
	if (lastRequestAt === undefined) return true;
	return now - lastRequestAt >= cooldown;
}
