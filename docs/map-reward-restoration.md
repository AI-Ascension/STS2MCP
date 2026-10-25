# Map and reward contract restoration

This local PR9 slice restores narrow visibility/index guards from verified ancestor
`4431b1e`, retaining the current player summaries, full map nodes and child paths.
The map serializer and choose action filter the same non-null, visible-in-tree,
travelable nodes. A visible-only map remains actionable. Reward serialization and
claiming likewise share visible, enabled, non-null reward filtering. Potion/relic
metadata and visible/enabled proceed readiness are restored from that ancestor.

Both SP and MP combat fallback branches now use the documented `rewards` state key,
as the overlay path and Markdown dispatcher already do. No dispatch ordering was
changed; the prior visible-map precedence fix is retained.

Validation (simulated controls, not game assemblies):
- `PATH=/tmp/sts-dotnet:$PATH python scripts/test_map_rewards.py`: 19 compiled checks.
- Existing reward dispatch harness: 104 compiled checks.
- The new harness against pre-slice `ac08502` compiles and fails on a null map node.
- Four deliberate regressions were rejected: hidden reward indexing, rejecting a
  visible-only map, hidden proceed readiness, and hidden map-node visibility.

The SDK path above is environment-specific; use a .NET 9 SDK on PATH elsewhere.
Actual game integration and whole-PR review remain separate gates.
