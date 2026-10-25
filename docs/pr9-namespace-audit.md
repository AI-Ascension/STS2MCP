# Restored partial-class import review

A final namespace-faithful test exposed an omitted compilation-unit import:
`BuildRestSiteState` references `NRestSiteButton`, which belongs to
`MegaCrit.Sts2.Core.Nodes.RestSite`. The import in `McpMod.Actions.cs` does not
apply to the separate `McpMod.StateBuilder.cs` partial-class compilation unit.
The StateBuilder import is now restored.

The event/rest regression harness now compiles the extracted StateBuilder and
Actions methods as separate source files, each with its actual production `using`
block. Its `NRestSiteButton` test double is declared only in the correct namespace.
Removing the StateBuilder import produces CS0246 in Production0.cs; adding it
passes all 28 event/rest behavior checks. Namespace placeholders permit unrelated
imports without pretending to supply game types. Other test-double types remain
simplified; this is not a full namespace-accurate game build.

A systematic comparison of all current top-level C# files against verified
ancestor `4431b1e` found only these remaining removed imports:

- StateBuilder `Models.Monsters`: associated with omitted ancestor pet helpers;
  current restored source has no unqualified concrete monster-class references.
- StateBuilder `Models.RelicPools`: current source reads `cm.RelicPool` as a
  property and has no concrete relic-pool type references.
- MultiplayerState `Godot`: newly restored tree/engine references are fully
  qualified as `Godot.SceneTree` and `Godot.Engine`.

All other ancestor imports are present in their respective changed compilation
units. This comparison is a restoration linkage check, not proof that every
external type/member matches the current proprietary game. Full game-linked
compilation remains an explicit unverified gate.
