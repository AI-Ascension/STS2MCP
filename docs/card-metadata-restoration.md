# Card metadata restoration (PR9)

- [x] Read AGENTS.md and endpoint contracts; isolate branch/worktree at c27a31fce2f84cb9c365f011adf3eb3fb72d6a1e.
- [x] Confirm missing helpers and current glossary/wiki callers.
- [x] Restore narrow helper closure and shared card serialization call sites from verified ancestor 4431b1e5a5c2e34fcc7dbcf5617236602e334f49.
- [x] Compile extracted production methods with .NET 9 direct Roslyn and test doubles: 51 checks, 4 representative mutations rejected.
- [x] Run static audit and record existing blockers; no full game build/runtime claim.

## Provenance and scope

`McpMod.StateBuilder.cs`: restored ancestor bodies for `GetCostDisplay`,
`GetStarCostDisplay`, `BuildCardInfo`, `BuildPileCardList`, `BuildDeckCardList`,
`GetPlayerDeckCards`, `GetMemberValue`, `GetBoolMemberValue`,
`AddCardHolderState`, and `IsCardHolderSelectable`. Added `using Godot` for
`Control` (the using is per compilation unit).

Adapted only serialization fragments of `BuildCardState`, `BuildShopState`,
`BuildCardRewardState`, `BuildCardSelectState`, `BuildChooseCardState`,
`BuildBundleSelectState`, and `BuildHandSelectState` to use ancestor shared
metadata. Retained base signatures, surrounding player-context dictionaries,
pricing (`cost` remains merchant price), selection order, and action-readiness
logic. Preserved Hand description context explicitly. Deck helpers are restored
for the separately owned player-context integration and are not wired to
`BuildPlayerState` here.

## Verification

`DOTNET=/tmp/sts-dotnet/dotnet python scripts/test_card_metadata.py --mutations`
passes 51 extracted-method assertions and rejects 4 representative mutations.
It compiles the actual production helper/serializer source with direct Roslyn,
uses test doubles for game types and visibility, and exercises existing clone
helpers from Helpers.cs. Covers normal/X/star costs, upgrade metadata and clone
non-mutation, failed/no previews, pile contexts/indexes, hand fields, deck
reflection, safe member access, and holder visibility/selection. Static checks
require all modified serialization contexts to call BuildCardInfo. This does
not compile complete screen builders or simulate the proprietary game.

`python scripts/audit_endpoints.py --skip-live` remains blocked by existing
`docs/raw-full.md` missing `GET /api/v1/bestiary`. Direct
`audit_static_card_glossary_metadata` now passes common metadata lookup but
fails at separately owned hand target metadata (`requires_target`). Broader
hand readiness, shop readiness, selection preview/counts, and player/run
context are intentionally outside this patch. No audits were weakened.

No game DLLs are available; no full mod build or live gameplay verification
was attempted. No MSBuild/security settings changed. No remote/public changes.
