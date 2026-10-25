# PR9 native restoration integration

## Completed local work

- Integrate profile, reward dispatch, fake merchant, menu actions, formatting,
  save context, shared card metadata, bridge and stable read-error restorations.
- Preserve interrupted hand/shop/selection metadata changes and test complete shop
  and grid-selection serializers; restore hidden/disabled button readiness.
- Restore player/potion, response-envelope, turn readiness, event/rest, menu/lobby,
  map/reward, selection-action, enemy and CrystalSphere state contracts.
- Reject stale enemy-target potion actions outside combat.
- Replace unsafe all-account save fallback with active-account isolation. A broad
  ancestor fallback was briefly integrated, then reverted after security review.
  Corrected behavior confines known accounts, rejects ambiguous unknown accounts,
  treats rooted paths as authoritative and preserves absolute snapshot roots.

## Remaining gates

- [x] Finish multiplayer game-over parity and run the complete static audit.
- [ ] Obtain fresh independent review of the final integrated candidate.
- [ ] Full proprietary game build and runtime validation (game DLLs unavailable).
- [ ] Public publication/approval/merge authorization and remote CI verification.

## Reproducible validation

Run `python scripts/run_native_restoration_checks.py --dotnet /path/to/dotnet`.
It runs focused scripts, selected mutation suites and the non-live endpoint audit.
It returns failure if any stage fails. Logs are stored separately and clearly state
that no real-game build/runtime validation occurs.

At `c959da1`, all 21 then-present focused scripts passed. The non-live audit passed docs,
actions, MCP tool contracts, formatters, errors, glossary, bestiary, cards,
account-isolated saves and snapshots; state coverage still requires multiplayer
`game_over` parity. This is an intermediate result, not final acceptance.

Follow-up independent review found additional readiness and bridge issues.
Corrections add disabled reward guards, pre-seed embark readiness, visible proceed
controls, preview-selection agreement, FTUE dispatch blocking, CrystalSphere
action visibility, structured no-profile errors, noncombat inventory Markdown and
profile restart-warning preservation. Multiplayer game-over parity is restored;
all static audit groups pass at `a3576f9`. The final aggregate/re-review remains
required after these refinements.

Coverage includes whole shop/grid serializers (27 checks), player/potion state and
action readiness (30), enemy/CrystalSphere state (16), selection guards (38),
turn readiness (67), event/rest (28), map/reward (19), hand metadata (58), save
account isolation (44), profile (17), read errors (12), merchant/proceed (37), menu/lobby
and formatters (29), reward dispatch (108), plus bridge, envelope, save-context,
ancestor-closure and mutation checks. Tests overlap; counts must not be summed as
independent coverage. Test doubles cannot prove proprietary API compatibility.

A direct Roslyn whole-project compile against the shipped stubs was attempted but
failed because those stubs lack existing game namespaces/types, including Shops,
Events.Custom, CharacterSelect and Saves. Stubs were not altered to conceal errors.
No full mod build or live gameplay pass is claimed.

The Python MCP server unit test runs with proxy variables removed only for that
process: inherited SOCKS configuration requires absent socksio, while this test
uses fake responses and constructs a real client without sending requests. No
production proxy or network setting was changed.
