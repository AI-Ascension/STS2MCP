# Event and rest readiness restoration

Restores the event/rest state and action contracts from verified ancestor
`4431b1e`, narrowly over integration base `4536c77`. Newer player summaries and
neighboring fake-merchant/reward flows are preserved.

- Events report the local mutable event when available, falling back to the
  canonical event. State and actions use the same visible-in-tree button list.
- Event locked/disabled options remain inspectable but cannot be clicked.
- Rest options come from visible UI controls, not a potentially differently
  ordered model list; model and UI enabled flags both gate choice.
- Proceed readiness includes visibility and enabled state.
- Ancestor event relic metadata is restored with the event serializer.

Validation: `PATH=/tmp/sts-dotnet:$PATH python scripts/test_event_rest.py`
passes 28 compiled checks against extracted production methods and simulated
models/UI controls. The pre-change base fails the mutable-event check. Five
intentional mutations (canonical-only event, removed event state/action
visibility, removed disabled guard, and enabled-only proceed readiness) all
fail the corresponding assertions. `git diff --check` passes.

These are simulated-control checks, not a build against actual game DLLs or a
live-game acceptance test. Existing generic index parsing behavior and ancient
dialogue detection are unchanged. No remote publication is included.
