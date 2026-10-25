# Stable 1.0.7 co-op correction bundle

This integration starts from stable `8032596` (1.0.6) and combines three
independently tracked corrections:

| Track | Original changes | Tracking |
| --- | --- | --- |
| Magma Dragoon first-slope rumble | `09a66af`, PR67 | `beads-eio.9.225` |
| Web Spider survivor ladder | `25f8004`, PR68 | `beads-eio.9.226` |
| X stored-charge HUD ownership | `7513962`, `74bc5e0` | `beads-eio.9.238` |

The production changes apply to separate code paths. The Magma and Web Spider
native regression harness additions overlapped at the scenario methods and CLI
choices; integration retains all three new entries: `magma_slope_rumble`,
`spider_ladder_pair` and `spider_ladder_survivor`, plus the independently
qualified `stock_charge_hud` case and its HUD-layout selector.

The framework remains `a251a98616f0c8f9e45c90c7ca71d20da71b8b21` and recomp-ui
remains `b964eabe5a3438b8ed121064354ba27c1accef3f`. Four-player code, free-cutscene
control, preview presentation changes and preview performance changes are not
part of this stable bundle. Diagnostic recording defaults remain off; public
packages must continue to exclude CD Speed, Fast Loading and development cheats.

## Combined checks completed

- The split, combat and lifecycle ownership suites compile and pass together
  against the stable framework headers. Split and combat use Clang C99 with
  `-Wall -Wextra -Werror`; lifecycle additionally suppresses the existing
  typedef-redeclaration and partial-initializer warnings. No unrelated warning
  cleanup is included.
- The combined native scenario harness parses and retains both tracks' methods.
- The hook-registration suite passes, including the new `800B2C8C` stock-HUD
  updater in both development and release recompiler configurations.
- `git diff --check` passes. Framework/UI pins and the title mod catalog retain
  their stable values.

Private integration receipts are retained under
`G:/Temp/Codex/psxrecomp/x4-stable-bug-audit/model-checks/`.

## Combined original-disc qualification

The native entry hook was regenerated from the stable framework; only generated
shard `SLUS_005.61_full_53.c` changed. The combined Windows development runtime
at `7cedeb2` passed all 39 CTests. Subsequent integration changes add regression
tools and qualification documentation only; production game code is identical.
The production builds also passed 39 Windows and 34 Linux CTests, using the
stable ENHANCED profile and LLE textured batching on both platforms.

- All 13 stage harness cases passed across five fresh hidden, muted processes.
  Both character orders cover Web Spider's P2 survivor descent and climb back,
  Sigma 1 survivor controls, damaging Magma slope descents with either leader,
  either-leader pillar fireballs with 16 actual terrain edits, and native
  P2-led Dragoon arena entry. Additional Web Spider controls cover either
  surviving P1 character and the both-alive P2 route. Dead partners and native
  lives remain unchanged during survivor checks.
- Four stored-shot HUD cases passed: X/P1 and X/P2 in local Split, and X/P2 in
  Unified with Stacked and Side by side HUDs. Real controller input creates
  four stored shots and consumes them through `4,3,2,1,0`; the test does not
  write the shot counter. Composed images show the original icons only beside
  X, with Zero's counter unchanged. The Split cases completed 1,818 render
  restoration checks with no mismatch, abort, watchdog or leaked transaction.
- Independent composed captures were inspected for the stored-shot icons,
  ladder descent/return, slope shake, terrain-breaking pillar event and live
  Dragoon arena. Both X seats retain the correct original HUD artwork.

Stage receipts remain under `x4-stable-bug-audit/native-qa/`; the four HUD
receipts and images remain under `x4-four-player/stock-hud/qa-x-*/` in the
task workspace. The private development binary SHA256 is
`b4fff6d171cc69476e3ca33035e6e3a5c6f6bc9e46e17fd15f5265a7d58e4395`.

## Artifact gates and scope limits

Public payload qualification is separate from the development fixture checks:
validate the extracted production executable, clean mod catalog, bundled BIOS,
version and execution stamps, diagnostics-off defaults, and absence of private
settings, saves and disc data. Package reports and extracted-artifact launch
receipts are retained by the release task before publication.

These checks cover the reported local mechanics and bounded controls. They do
not establish a full-campaign audit or a fresh online gameplay qualification.
The online HUD scope was source-audited against the existing private-view
transaction contract; it was not counted as a network gameplay pass. Four-player
stored-shot ownership and centered three-player presentation remain feature-only
and require their own native qualification.
