# Selection guard restoration

This local candidate restores thirteen selection actions and six matching state
serializers from verified ancestor `4431b1e`, retaining newer player summaries.
Map/reward dispatch, merchant behavior and menu actions are not replaced.

Selections now reject hidden or disabled controls and filter empty holders
consistently with their serialized indexes. Bundle indexes deliberately include
visible but disabled bundles: state reports `can_select: false` and the action
rejects that exact index rather than silently selecting the next enabled bundle.
This corrects a mismatch present even in the ancestor. Treasure state and actions
both exclude holders without relic models and hidden collections; hidden chest
buttons are not automatically clicked.

`python scripts/test_selection_guards.py --dotnet /tmp/sts-dotnet/dotnet`
compiles the actual thirteen action methods and six serializer methods with
simulated Godot/UI/model classes. It checks 37 behaviors across card rewards,
grid/choose-card controls, bundles, combat hand selection, relics and treasure.
Five optional `--mutation` cases verify the harness rejects omitted filters,
shifted bundle indexes, null treasure/hand holders and hidden confirmation.
`--revision ac08502` reproduces the original failure.

The helper/model doubles isolate control-flow and indexing behavior. They do not
prove proprietary API compatibility, rendering, asynchronous UI transitions,
network behavior or real-game operation. Existing compiler nullable warnings
remain. The separate PR8 enchant-preview cancellation fix is not included in this
PR9-specific branch and must be preserved when the two branches are combined.
