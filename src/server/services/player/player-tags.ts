/**
 * The player lifecycle as CollectionService tags (ADR 0008).
 *
 * PlayerService adds PlayerPending on join; PlayerProfile adds PlayerLoaded
 * once the profile is in memory. Bind a component to the tag whose guarantee
 * it needs: PlayerLoaded means the profile, PlayerDataNode, and
 * PlayerCharacter all exist for that player.
 */
export const PLAYER_PENDING_TAG = "PlayerPending";
export const PLAYER_LOADED_TAG = "PlayerLoaded";
