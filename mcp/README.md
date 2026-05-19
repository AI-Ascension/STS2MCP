# MCP Tools

## Singleplayer

| Tool | Scope | Description |
|---|---|---|
| `get_game_state(format?, wait_for_actionable?, wait_timeout?, poll_interval?)` | General | Get current game state (`markdown` or `json`), optionally waiting through transient non-actionable states |
| `log_agent_decision(summary, reasoning?, intended_action?, alternatives?, confidence?, tags?)` | General | Add a structured decision annotation to the run log |
| `log_external_token_usage(usage_json)` | General | Attach exact/external model token usage to a run log event or tool call |
| `log_model_message(role, content, source?, turn_id?, turn_index?, message_id?, related_tool_call_id?, related_event_id?, state_sha256?, content_preview?, exact_*_tokens?, token_source?, model?)` | General | Attach prompt/completion/message records to a stable conversation turn |
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

## Bridge Configuration

The Python MCP bridge reads connection settings from the process environment and then from `mcp/.env` for unset keys. Environment variables always win over `.env` values.

Supported settings:

| Setting | Default | Purpose |
|---|---|---|
| `STS2_HOST` | `localhost` | Hostname or IP address for the STS2_MCP HTTP listener |
| `STS2_PORT` | `15526` | Port for the STS2_MCP HTTP listener |
| `STS2_MCP_AUTH_TOKEN` | unset | Optional bearer token sent by the MCP bridge as `Authorization: Bearer <token>` |

`STS2_MCP_AUTH_TOKEN` does not make the game mod enforce authentication. It only controls the HTTP headers sent by the MCP bridge, which is useful when the bridge talks through an authenticated proxy/tunnel or a future listener that validates bearer tokens.

`mcp/.env` supports simple `KEY=value` entries, optional `export`, quoted values, and inline comments after whitespace. Tokens containing `#` are preserved when the hash is part of the value, for example `STS2_MCP_AUTH_TOKEN=abc#123`. Local `.env` files are ignored by git.

## Multiplayer

All multiplayer tools are prefixed with `mp_`. They route through `/api/v1/multiplayer` and are only available during multiplayer (co-op) runs. The endpoints automatically guard against cross-mode calls.

If the game mod is launched on a non-default port with `STS2_PORT`, start the MCP bridge with the same port, for example `python server.py --port 15527`. The game listener reads its port at game startup; the MCP bridge reads its own connection settings when the bridge process starts.

| Tool | Scope | Description |
|---|---|---|
| `mp_get_game_state(format?, wait_for_actionable?, wait_timeout?, poll_interval?)` | General | Get multiplayer game state (all players, votes, bids), optionally waiting through transient non-actionable states |
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

## Run Logging

The MCP bridge writes structured JSONL logs by default under `logs/run_<timestamp>-<id>.jsonl` relative to the server working directory. It also writes `logs/run_<timestamp>-<id>.summary.json` with run-level token rollups. Each JSONL line has a stable envelope with `schema_version`, `token_schema_version`, `run_id`, `event_id`, `sequence`, UTC `timestamp`, `monotonic_ms`, `event_type`, token fields, and when applicable `tool_call_id` / `tool_name`.

Logged events include:

- `session_start` with bridge configuration and runtime metadata.
- `tool_call_start`, `tool_call_result`, and `tool_call_error` for every MCP tool.
- `http_request`, `http_response`, and `http_error` for calls to the STS2_MCP REST API.
- `state_poll` and `state_poll_final_format` for smart polling decisions.
- `agent_decision` entries from `log_agent_decision`.
- `external_token_usage` entries from `log_external_token_usage`.
- `model_message` entries from `log_model_message`.

Tool and HTTP results include length, byte count, SHA-256, preview text, truncation status, and estimated token count. Keys containing `authorization`, `cookie`, `password`, `secret`, `token`, `api_key`, or `apikey` are redacted before writing.

Every record includes:

- `input_tokens`
- `output_tokens`
- `tool_response_tokens`
- `hidden_poll_tokens`
- `total_tokens`
- `token_source`
- `tokenizer_name`
- `tokenizer_version`
- `model_family`
- `estimation_method`

By default these counts use a deterministic regex estimator (`generic_regex_v1`) so runs remain comparable without installing model-specific tokenizers. Treat these as estimates, not provider-billed tokens. Use `log_external_token_usage` to attach exact model API usage when a client has it:

```json
{
  "related_tool_call_id": "9f...",
  "model": "claude-sonnet-4.6",
  "input_tokens": 1200,
  "output_tokens": 400,
  "token_source": "exact"
}
```

Use `log_model_message` to attach first-class prompt and turn structure:

```json
{
  "role": "user",
  "content": "Choose the best card to play.",
  "source": "agent-wrapper",
  "turn_id": "run-1-turn-7",
  "turn_index": 7,
  "message_id": "msg-007-user",
  "state_sha256": "..."
}
```

Message roles are `system`, `user`, `assistant`, `tool`, `developer`, and `external`. Each `model_message` record stores `message_id`, `turn_id`, `turn_index`, role/source, content hash, bounded preview metadata, estimated tokens, optional exact token usage, privacy flags, and related `tool_call_id` / `event_id` links when supplied. If `turn_id` or `message_id` is omitted, the bridge generates stable IDs for the current run. Set `content_preview=false` to keep hashes and counts while omitting prompt preview text.

The summary artifact rolls up totals by tool name, event type, state type, game mode, action category, run phase, floor, token source, turn, role, and message source where available. It also tracks total prompts, total turns, average tokens per turn, tool-result token share, hidden polling token share, hidden polling cost, largest prompts, largest payloads, repeated-state cost, invalid-action cost, replay artifact size/token metadata, and externally supplied usage records.

Logging options:

```bash
python server.py --log-dir logs
python server.py --disable-run-log
python server.py --log-preview-chars 8000
python server.py --log-full-text
python server.py --tokenizer-profile openai_cl100k_proxy
python server.py --token-model-family anthropic --tokenizer-name claude_proxy_regex
```

`STS2_MCP_LOG_DIR` can also set the default log directory. Use `--log-full-text` when you need complete replayable tool/API text for evaluation; otherwise previews plus hashes keep the log smaller while preserving integrity checks. Token estimates are computed from the full text before truncation, even when only previews are written.

Validate a log and its summary:

```bash
python validate_run_log.py --self-test
python validate_run_log.py logs/run_<timestamp>-<id>.jsonl
```

The validator checks JSONL parseability, strictly increasing sequence numbers, unique `event_id` values, non-decreasing monotonic time, token field consistency, summary rollup consistency, model-message roles, monotonic first-seen turn ordering, message-to-turn linkage, external-usage-to-message reconciliation, and a deterministic tokenizer fixture.

Privacy notes:

- Token counts are computed after recursive redaction for structured arguments and metadata.
- Response text is counted before preview truncation, but full response text is stored only with `--log-full-text`.
- `log_model_message` stores prompt previews by default. Pass `content_preview=false` when clients need hash/token accounting without prompt text snippets.
- External usage records may reveal provider/model information supplied by the client; redact those fields client-side if needed.

## Smart State Polling

`get_game_state` and `mp_get_game_state` default to `wait_for_actionable=true`. The bridge polls JSON state until one of these conditions is met, then returns the requested format:

- combat reaches the player's play phase;
- event dialogue/options are available;
- reward, rest, shop, treasure, or Crystal Sphere controls are actionable;
- another non-transient state is reached;
- `wait_timeout` expires.

Set `wait_for_actionable=false` to get the immediate raw state. `wait_timeout` is capped at 60 seconds and `poll_interval` is capped between 0.1 and 5 seconds.
