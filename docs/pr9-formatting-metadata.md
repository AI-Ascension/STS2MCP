# PR9 formatting metadata repair

Base: `c27a31fce2f84cb9c365f011adf3eb3fb72d6a1e`.
Verified common ancestor: `4431b1e5a5c2e34fcc7dbcf5617236602e334f49`.

## Provenance and boundaries

- `FormatUpgradeMarker`, `FormatCardDetails`, `FormatRelicDetails`, and
  `FormatKeywordNames` are byte-for-byte copies of the ancestor methods.
- Restored ancestor helper call expressions in single-player hands, card rewards,
  card/hand selection (including selected cards), bundles and previews, relic
  selection and treasure. Multiplayer hands/relics use the same contract while
  retaining PR9's separate multiplayer formatter and nested player layout.
- Draw/discard/exhaust rows use the ancestor `FormatPileMarkdown` row expression
  (`FormatCardDetails(card, energyLabel: false)`), without replacing the PR9 pile
  method or changing pile ordering/counts.
- The shop card-cost/upgrade-preview block and card switch arm are copied from
  the ancestor. Shop keyword associations use the ancestor helper. Current shop
  purchase-price key `cost`, availability, sale and affordability remain intact;
  this is not a revert to the ancestor's `price` schema. Potion/relic descriptions
  retain PR9 fields; no unsupported rarity/usage fields were invented.
- Actual PR9 producers already emit structured keyword dictionaries, upgrade
  flags, and star costs for card selections. The old formatter's `List<string>`
  branches silently discarded per-card keyword associations; the glossary alone
  did not identify which card had a keyword.
- Pile/shop metadata producer restoration is in the separate card-metadata
  change. No state builders, actions, routes, saves or bridge files are modified
  here. No whole-file ancestor overwrite; fake-merchant additions integrate
  separately and are not removed.

## Verification

Run `PATH=/tmp/sts-dotnet:$PATH python scripts/test_formatting_metadata.py --mutations`
(or put a .NET 9 SDK on PATH). Uses Roslyn directly, never MSBuild or its mutex.
SDK used: **9.0.319**. Compiles the entire real standalone Formatting.cs alongside
an independent dictionary-fixture harness; no copied formatting implementation
or game-model mocks are involved.

- Original base source: compiles, **40 of 71 assertions fail** (red reproduction).
  Original SHA256: `b679958c3deec83aab4c831975526966ef0d0c46742e846038eb012da6122f23`.
- Repaired source: **71/71 pass**. Covers SP/MP hand target/playability, all card
  selection paths, bundles and previews, relic counters/selection/treasure,
  three pile kinds, all shop categories, price vs energy/star cost, upgrade
  previews and unchanged-preview omission, missing/null/empty optionals, full
  state dispatch and retained glossary.
- Eight compiling semantic mutations are rejected: suppress keyword names,
  upgrade marker, star cost, relic keywords, bundle details, hand details, pile
  details, and shop upgrade preview. Each fails assertions, not compilation.
- Existing `audit_static_formatters` from the bridge audit passes against this
  tree. `git diff --check` passes.

This is compiled formatter verification only, not a full mod build or live game
validation. The proprietary game/Godot dependency boundary remains untested.
