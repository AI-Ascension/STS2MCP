# Native save-context restoration provenance

Local-only branch `native-restore-save-context`, based on `c27a31fce2f84cb9c365f011adf3eb3fb72d6a1e`.
Reference ancestor: `4431b1e5a5c2e34fcc7dbcf5617236602e334f49`.

## Narrow restored closure

- `McpMod.Compendium.cs`: `BuildActiveRunContext`, general `BuildCurrentRunContext` overload and snapshot wrapper, general `ResolveCurrentRunPath` overload and snapshot wrapper, `SortDictionaryListByStringField`; normalized response context/history/save paths; resolved progress snapshot field; deterministic discovery/card/character/fight-stat ordering.
- `McpMod.StateBuilder.cs`: end-of-active-state `current_run` and top-level `player` assignments.
- `McpMod.MultiplayerState.cs`: equivalent current-run/local-player tail, preserving existing all-players output.
- These are selected ancestor fragments, not whole-file replacement. No error handlers, method status codes, card helper bodies, room dispatch, save-root discovery or filesystem authorization logic changed.

History supporting this contract includes `a6b0feb` (active-run state context), `8817e98` (compendium context), `d5024e5` (resolved paths), `c5ae36c` (current-run enrichment), `c95f601` (deterministic metadata), `aa3454a` and `1698771` (JSON path normalization). Player-tail provenance additionally includes `47c18fb` (singleplayer) and `eeadae6` (multiplayer). The existing `Profile` and `ForkEndpoints` callers already require the restored overload and sorting helper. Existing raw docs and audit checks require current-run identity/save context at these boundaries.

## Verification

`python scripts/test_save_context.py --dotnet-root /tmp/sts-dotnet`

Passes actual source-extracted C# compilation using direct Roslyn from SDK 9.0.319 and .NET 9.0.21 reference/runtime assemblies. Fixtures are created under a temporary directory inside this checkout and removed afterward. Controlled save-root and game-singleton stubs prevent discovery of real user saves. Checks include absent manager/run, inactive run, unsaved limitation (no invented ID), normalized relative/modded profile paths, save-backed scalar/seed/identity, snapshot/general overload parity, later-root resolution, absolute-active-location precedence, malformed/missing save fields and nonmutating ordinal sorting. Five deliberate behavioral mutations must fail: bypass normalization, corrupt run identity, remove inactive gating, reverse sort, and remove active-path precedence. Source checks additionally verify response and SP/MP callsites.

`git diff --check`: passes.
Existing `audit_static_bestiary_determinism`: passes.
Existing `audit_static_save_roots`: fails on base's restrictive account discovery (`accountRoots.Count == 1`), unrelated to the restored closure; intentionally not broadened.
Existing aggregate `python scripts/audit_endpoints.py --skip-live`: stops on pre-existing docs missing `GET /api/v1/bestiary`.

This is not full mod compilation or a live-game claim. The extracted harness validates the closure with controlled game stubs, not actual game assemblies, scene wiring, concurrent save writes, or platform-specific native filesystem behavior. No public writes, cloud task continuation, game execution, real save discovery or permission changes were performed.
