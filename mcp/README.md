# MCP Tools

## Singleplayer

| Tool | Scope | Description |
|---|---|---|
| `get_api_index()` | General | Get mod status, bound prefixes, and HTTP endpoint index |
| `get_game_state(format?)` | General | Get current game state (`markdown` or `json`) |
| `menu_select(option, seed?)` | General | Select a visible menu/game-over option |
| `get_profile()` | Profiles | Get active profile progress |
| `get_compendium()` | Profiles | Get active profile progress grouped like the in-game Compendium |
| `search_wiki(query, item_type?, limit?)` | Profiles | Fuzzy-search discovered card and relic wiki entries |
| `list_profiles()` | Profiles | List profile slots and active slot |
| `switch_profile(profile_id)` | Profiles | Switch to a profile slot through the game UI |
| `delete_profile(profile_id)` | Profiles | Delete an inactive profile slot |
| `list_snapshots()` | Snapshots | List current-run save snapshots and snapshot feature status |
| `create_snapshot()` | Snapshots | Create a snapshot from the active profile's current run save |
| `resume_snapshot(snapshot_id)` | Snapshots | Restore a snapshot to the active profile's current run save slot |
| `use_potion(slot, target?)` | General | Use a potion (works in and out of combat) |
| `discard_potion(slot)` | General | Discard a potion to free up the slot |
| `proceed_to_map()` | General | Proceed from rewards/rest site/shop/treasure to the map |
| `combat_play_card(card_index, target?)` | Combat | Play a card from hand |
| `combat_end_turn()` | Combat | End the current turn |
| `combat_select_card(card_index)` | Combat Selection | Select a card from hand during exhaust/discard prompts |
| `combat_confirm_selection()` | Combat Selection | Confirm the in-combat card selection |
| `rewards_claim(reward_index)` | Rewards | Claim a reward from the post-combat screen |
| `rewards_pick_card(card_index)` | Rewards | Select a card from the card reward screen |
| `rewards_skip_card()` | Rewards | Skip the card reward |
| `map_choose_node(node_index)` | Map | Choose a map node to travel to |
| `rest_choose_option(option_index)` | Rest Site | Choose a rest site option (rest, smith, etc.) |
| `shop_purchase(item_index)` | Shop | Purchase an item from the shop |
| `event_choose_option(option_index)` | Event | Choose an event option (including Proceed) |
| `event_advance_dialogue()` | Event | Advance ancient event dialogue |
| `deck_select_card(card_index)` | Card Select | Pick/toggle a card in the selection screen |
| `deck_confirm_selection()` | Card Select | Confirm the current card selection |
| `deck_cancel_selection()` | Card Select | Cancel/skip card selection |
| `bundle_select(bundle_index)` | Bundle Select | Open a bundle preview |
| `bundle_confirm_selection()` | Bundle Select | Confirm the current bundle preview |
| `bundle_cancel_selection()` | Bundle Select | Cancel the current bundle preview |
| `relic_select(relic_index)` | Relic Select | Choose a relic from the selection screen |
| `relic_skip()` | Relic Select | Skip relic selection |
| `treasure_claim_relic(relic_index)` | Treasure | Claim a relic from the treasure chest |
| `crystal_sphere_set_tool(tool)` | Crystal Sphere | Switch the active divination tool |
| `crystal_sphere_click_cell(x, y)` | Crystal Sphere | Click a hidden cell in the grid |
| `crystal_sphere_proceed()` | Crystal Sphere | Continue after the minigame finishes |

### Profile Tools

`get_profile()` returns the raw active-profile progress summary: character totals, global totals, discoveries, achievements, epochs, and aggregate stats.

`get_compendium()` presents the same profile data in the shape agents usually need when reasoning about long-term progress. It groups the response into `card_library`, `relic_collection`, `potion_lab`, `bestiary`, `character_stats`, and `run_history`, matching the high-level Compendium cards in the game UI. It also includes `current_run` while a run is active, with a derived `run_id` in `{save_scope}:profile{profile_id}:{start_time}` format.

The Compendium response is profile-scoped, not run-state-scoped. It works from the main menu, does not require navigating the in-game Compendium UI, and summarizes only the 20 most recent saved run-history files to keep the MCP response bounded.

Profile switch/delete failures are surfaced as structured endpoint errors with HTTP 400 for invalid input and HTTP 409 for state conflicts such as deleting the active profile or switching during a run.

Snapshot capture is opt-in. Launch the game with `STS2_MCP_SNAPSHOTS=1` to create a snapshot every time the game saves `current_run.save` or `current_run_mp.save`. Set `STS2_MCP_SNAPSHOT_DIR` to override the snapshot directory. `resume_snapshot()` restores a selected snapshot on disk and is rejected while a run is in progress; continue from the in-game menu after restoring.

POST validation failures preserve endpoint `error_code` values such as `invalid_json`, `missing_action`, `invalid_action_type`, `missing_profile_id`, `invalid_profile_id_type`, and `invalid_action_payload`.

Route-level failures preserve endpoint `error_code` values such as `method_not_allowed`, `not_found`, and `internal_error`.

Read endpoint startup/data-availability failures preserve endpoint `error_code` values such as `save_manager_unavailable`, `settings_data_unavailable`, and `profile_data_unavailable`.

Read endpoint exceptions preserve endpoint-specific `error_code` values such as `settings_read_failed`, `bestiary_build_failed`, `glossary_build_failed`, `profile_build_failed`, `profiles_read_failed`, `compendium_build_failed`, `singleplayer_state_read_failed`, and `multiplayer_state_read_failed`.

Menu/action dispatch failures also use structured endpoint errors: missing or unknown main-menu selections and unknown actions return HTTP 400, gameplay actions sent without an active run return HTTP 409, Timeline manual-reveal blocks return HTTP 409 with `error_code: timeline_manual_action_required`, and blocking tutorial/popup overlays return HTTP 409 with `error_code: blocking_popup_active`. Older generic action failures carry the stable fallback `error_code: action_error` instead of omitting an error code. Other failed actions return non-2xx structured error JSON instead of HTTP 200. MCP wrappers preserve those structured JSON error bodies and add `http_status` so callers can handle endpoint failures without parsing a flat text prefix.

Glossary tools require an active run. They include the current character context plus shared run pools such as Colorless cards, shared relics, and shared potions. Card glossary items include energy/star costs, upgrade availability, plus upgraded-preview cost and description. Successful responses include `profile_id`, `progress_path`, `resolved_progress_path`, `profile_root`, `save_scope`, `current_run` save context, `kind`, `count`, and `items`; `current_run.run_id` and `current_run.seed` are included when `current_run.save` exposes them. The HTTP endpoints return `run_not_in_progress` with HTTP 409 when called from the main menu, or `run_state_unavailable` with HTTP 503 if the active run state cannot be read, while still including the active profile/save context fields.

## Multiplayer

All multiplayer tools are prefixed with `mp_`. They route through `/api/v1/multiplayer` and are only available during multiplayer (co-op) runs. The endpoints automatically guard against cross-mode calls.

If the game mod is launched on a non-default port with `STS2_PORT`, start the MCP bridge with the same port, for example `python server.py --port 15527`. The game listener reads its port at game startup; the MCP bridge reads its own connection settings when the bridge process starts.

| Tool | Scope | Description |
|---|---|---|
| `mp_get_game_state(format?)` | General | Get multiplayer game state (all players, votes, bids) |
| `mp_combat_play_card(card_index, target?)` | Combat | Play a card from the local player's hand |
| `mp_combat_end_turn()` | Combat | Submit end-turn vote (turn ends when all players submit) |
| `mp_combat_undo_end_turn()` | Combat | Retract end-turn vote |
| `mp_use_potion(slot, target?)` | General | Use a potion from the local player's slots |
| `mp_discard_potion(slot)` | General | Discard a potion from the local player's slots |
| `mp_proceed_to_map()` | General | Proceed from rewards/rest site/shop/fake merchant/treasure to the map |
| `mp_map_vote(node_index)` | Map | Vote for a map node (travel when all agree) |
| `mp_event_choose_option(option_index)` | Event | Vote for / choose an event option |
| `mp_event_advance_dialogue()` | Event | Advance ancient event dialogue |
| `mp_rest_choose_option(option_index)` | Rest Site | Choose a rest site option (per-player, no vote) |
| `mp_shop_purchase(item_index)` | Shop | Purchase an item (per-player inventory) |
| `mp_rewards_claim(reward_index)` | Rewards | Claim a post-combat reward |
| `mp_rewards_pick_card(card_index)` | Rewards | Select a card from the card reward screen |
| `mp_rewards_skip_card()` | Rewards | Skip the card reward |
| `mp_deck_select_card(card_index)` | Card Select | Pick/toggle a card in the selection screen |
| `mp_deck_confirm_selection()` | Card Select | Confirm the current card selection |
| `mp_deck_cancel_selection()` | Card Select | Cancel/skip card selection |
| `mp_bundle_select(bundle_index)` | Bundle Select | Open a bundle preview |
| `mp_bundle_confirm_selection()` | Bundle Select | Confirm the current bundle preview |
| `mp_bundle_cancel_selection()` | Bundle Select | Cancel the current bundle preview |
| `mp_combat_select_card(card_index)` | Combat Selection | Select a card during in-combat selection prompts |
| `mp_combat_confirm_selection()` | Combat Selection | Confirm in-combat card selection |
| `mp_relic_select(relic_index)` | Relic Select | Choose a relic from the selection screen |
| `mp_relic_skip()` | Relic Select | Skip relic selection |
| `mp_treasure_claim_relic(relic_index)` | Treasure | Bid on a relic (relic fight if contested) |
| `mp_crystal_sphere_set_tool(tool)` | Crystal Sphere | Switch the active divination tool |
| `mp_crystal_sphere_click_cell(x, y)` | Crystal Sphere | Click a hidden cell in the grid |
| `mp_crystal_sphere_proceed()` | Crystal Sphere | Continue after the minigame finishes |
