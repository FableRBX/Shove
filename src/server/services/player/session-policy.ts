/**
 * Pure decisions for the profile session lifecycle. PlayerService and
 * PlayerDataNode are thin shells over these.
 */

export interface SessionEndContext {
	/** This server ended the session itself (normal leave or failed setup). */
	intentional: boolean;
	/** ProfileStore.IsClosing: the server is shutting down and every session ends. */
	serverClosing: boolean;
	/** The player is still in the game. */
	playerPresent: boolean;
}

/**
 * A session that ends for any reason other than our own EndSession or a server
 * shutdown was stolen by another server; the player must rejoin to get their
 * data back.
 */
export function shouldKickOnSessionEnd(ctx: SessionEndContext): boolean {
	return !ctx.intentional && !ctx.serverClosing && ctx.playerPresent;
}

/**
 * Seconds to keep retrying a profile load before giving up and kicking. Matches
 * ProfileStore's own START_SESSION_TIMEOUT, which passing a Cancel condition
 * otherwise disables. Covers the ~40s session-steal wait on a quick rejoin.
 */
export const PROFILE_LOAD_TIMEOUT = 120;

/** Stop retrying a profile load once the player is gone or the timeout is reached. */
export function shouldCancelProfileLoad(playerPresent: boolean, elapsed: number, timeout: number): boolean {
	return !playerPresent || elapsed >= timeout;
}
