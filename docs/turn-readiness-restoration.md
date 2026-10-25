# End-turn readiness restoration

Restores the three end-turn readiness helpers and battle metadata from verified ancestor `4431b1e`, retaining the newer single-player player shortcut and multiplayer players collection. Action guards already remain in the PR9 baseline and are unchanged.

Validation: `PATH=/tmp/sts-dotnet:$PATH python scripts/test_turn_readiness.py` compiles the actual SP/MP battle builders and readiness helpers with simulated controls. All 67 assertions pass, including missing combat, play phase, disabled actions, hand modes, dead/ready players, missing combat state, undo readiness, local-player absence, and retained player shortcuts. `--baseline` compiles the original integration baseline and fails on absent `can_end_turn`, demonstrating the regression.

These are simulated-control tests, not real-game or full-project build proof. The nullable warnings stem from the fixture's nullable combat singleton, not a new production API contract. Existing action handlers are not rewritten or newly validated by this slice.
