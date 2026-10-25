# Menu state and formatting restoration

Restores the non-run menu inspection, character/lobby/join/load helpers and menu/game-over formatter methods from verified ancestor `4431b1e`. It preserves the current status/kind envelope and does not replace the in-run reward/fake-merchant dispatch. A specific game-over branch precedes generic overlays; menu formatting precedes generic message early-return so available actions remain visible.

Verification: `PATH=/tmp/sts-dotnet:$PATH python scripts/test_menu_closure.py --mutations` compiles the restored no-run/null-run/FTUE prefix and every menu/lobby helper against simulated scene/lobby classes, and compiles the entire real formatting file. It checks 29 conditions and rejects menu and game-over formatter dispatch mutations. `test_reward_dispatch.py` compiles the actual in-run dispatch (menu prefix separately covered), including game-over precedence. `test_state_envelopes.py` runs the menu suite plus its MP prefix checks. Existing formatting metadata regression suite remains green.

These tests do not prove compatibility with proprietary game assemblies or current live UI. Scene/reflection field assumptions derive from the ancestor; actual game integration and fresh independent review are still required.
