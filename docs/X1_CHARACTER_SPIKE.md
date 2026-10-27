# X1 character replacement spike

Branch: `spike/x1-character-replacements`, based on stable `master` at
`54088ed37fa2879aa51d36c3934bba676e0380a6` (1.0.12). This branch does not
include the game's four-player co-op implementation.

Visual correction is in progress. The earlier control, damage and snapshot
checks did not qualify the atlas poses: they missed swapped walk/jump frames,
incorrect firing poses, neighboring sprite fragments and a projectile-impact
image drawn as a charge indicator. Do not treat the earlier handoff as a
complete animation or X1 parity qualification.

Enable **X1 X** and/or **X1 Zero** under Characters, then boot the game. They
are independent opt-in packages, both off by default. OpenGL is required for
the supplied PNG sprite replacements. A fresh boot is required after changing
character packages. The original supported US game disc remains required.

- X1 X overrides every X armor form, suppresses Ultimate Armor and all X4
  armor capabilities, and retains X4 boss weapons earned in the campaign.
- X1 Zero overrides ordinary/Black Zero, uses a chargeable Z-Buster, ground
  dash and wall kicks/climbing, and suppresses the saber, learned X4 saber
  techniques, air dash and double jump. Zero was not playable in X1: this is
  an explicitly playable interpretation of that design.
- The mods retain each character's story identity, health HUD and native
  pause menu. Saved armor progress remains in the native progress bytes;
  temporary capability reads are adapted around ordinary guest calls.

This is an X1-inspired mechanics/art spike over X4's original collision,
movement, damage and weapon engine, not a cycle-exact port of SNES physics.
X4's story, dialogue, portraits, boss weapons and stage interactions remain
native. The provided sheets do not contain every X4-specific scripted,
vehicle or menu animation; those use available replacement poses rather than
invented art. Exact X1 timing/damage, bespoke vehicle poses, all stage/boss
interactions and netplay still require broader qualification.

## Original artwork

The supplied files are preserved byte for byte:

| Package resource | Original | SHA-256 |
| --- | --- | --- |
| X sheet; Zero's projectile sheet | `x.png`, 1200 x 1700 RGBA | `38aac56e91351362f2924ef959556dc64be12948d630abcc6861703d90b3c191` |
| Zero sheet | `zero.png`, 1023 x 567 RGB | `7fff0307f7c224be18ca592f9f4a6daf985014732eca5c625ccde521a77cac0b` |

Zero's sheet credits **the_wanderer**. The supplied X sheet does not identify
its artist. Each package carries a provenance file; retain that attribution
gap when considering a future public distribution. No AI reconstruction,
bitmap rewriting or offline resampling was used. Zero's blue sheet background
is keyed out while decoding the immutable texture bank.

## Implementation

`mmx4_x1_frames.json` describes bounded rectangles in the original PNGs.
`generate_x1_frames.py` generates only C++ atlas metadata. Packages verify
resource size/hash before activation. The renderer samples those rectangles
into immutable RGB555 texture banks. Dash trails use separate translucent
banks; private local camera rendering has separate packet arenas/cursors.
Current-build snapshots serialize canonical packet cursors and solo private
sound-bank state, then reconstruct derived banks on restoration.

`mmx4_x1.c` scopes original guest movement/projectile calls. Zero temporarily
uses X's ordinary movement/buster resources; its logical character, campaign,
stats and scratch resources are restored before returning. Doors, arrivals,
scripted actions, vehicles and death retain original logical control. Native
air dash (`8003484C`) and double jump (`800347D0`) are blocked for these forms;
ground dash (`80034754`) remains available. Normal, medium and full buster
projectiles are native classes 0, 9 and 18. The private VAB/sample-bank path
supplies X's buster effects while preserving Zero's character voice bank.
The native projectile collision runs after the temporary X movement context
has ended. Its buster-impact request is separately scoped to X's effects
bank; ordinary Zero voices and pickup sounds retain their original routing.
Iris has no original buster admission rows. X1 Zero reuses her native Zero
reaction rows for buster hits, preserving armor exposure and cooldowns in
solo and co-op; it keeps the original projectile identity and consumption.

The shared framework pin `2f3f38403250b2937cf61179a17dc648c3392765` is already
published on `mstan/psxrecomp`'s `spike/mmx4-four-player` branch. It supplies
format-11 package disablement and the qualified texture/snapshot APIs. This
pin does not enable the game's separate four-player mod.

## Validation

Source/unit checks cover package defaults, verified resources, armor package
suppression, saved progress/identity restoration, reentry/snapshot guards,
script/vehicle exclusion and private audio/voice selection. Native hidden,
muted tests use private settings and memory cards plus the original disc.
The co-op scenario is reproducible with:

```powershell
python tools/test_mmx4_coop_regressions.py `
  --exe <development-build>/MegaManX4Recomp.exe `
  --bios <development-build>/bios/openbios.bin `
  --disc <original-disc.cue> --game game.toml --output <new-private-directory> `
  --hidden-window --quick-boot --local-cameras split --cameras split `
  --x1-x --x1-zero --campaign 0 --cases x1_characters x1_buster_damage personal_menus
```

Repeat with `--campaign 1` to reverse the character/seat assignment. Fixtures
prepare stage/progress/positions only. Controller input drives movement,
normal and charged firing and the selected X4 weapon. The scenario checks
native character identity, stored armor suppression, independent seats and
current-build save/load, retaining composed captures and JSON observations.

| Check | Result |
| --- | --- |
| Windows CTest suite | 41/41 passed, including native Zero assembly decoding and scoped buster-impact audio |
| Solo X and solo Zero | Movement, normal/full charge, pause/resume, current-build save/load passed |
| Both co-op campaigns/seat assignments | Ground dash, jump, air-dash suppression, buster charge, retained X4 weapon, saved armor suppression and save/load passed |
| Buster damage in both seats | Original damage-store PC `8002DF0C` reduced real enemy HP; no damage result was written by a fixture |
| Independent native menus | Weapons, E-tanks, Quit/Options, surviving P2 and paused save/load passed in both campaigns; render verification reported no mismatches or VRAM leaks |
| Iris as buster-only Zero | Native armor exposure, exposed-core defeat and actual section1 entry passed; core HP was explicitly prepared at4 to bound the test, so this does not claim a full48HP defeat |
| All stages, bespoke poses, exact SNES physics/damage, netplay, other host platforms | Unverified for this spike |

The Iris check is available as `--campaign 1 --cases x1_iris_buster` with
the same private runner arguments. Private runs keep neutral controller
overrides between pulses, so physical owner devices cannot affect QA.

Tracking: central Beads `beads-eio.9.263` (X), `beads-eio.9.264` (Zero).

## Remaining parity and qualification gaps

Current visual follow-up: `beads-eio.9.265`. Original PNG files are unchanged.
Full presented-frame histories are captured with controller routes bounded by
native frame counts; matching RAM snapshots identify the action actually
shown. A successful input/health assertion alone is not a visual pass.

| Area | Current implementation and remaining work |
| --- | --- |
| X walk/jump/fire artwork | Atlas mappings corrected; native visual review in progress. Walk/fire, jump/fire and dash/fire have separate sequences. |
| X wall/ladder/damage | Wall rectangles and damage pose corrected. Wall and ladder route coverage still needs native visual review. |
| Zero idle and ground movement | Side-facing idle uses the supplied sheet. Neutral ground start/run/stop use original-disc Zero graphics, assembly and palettes, decoded into immutable texture banks; firing returns to the supplied cannon-out artwork. These are native X4 neutral poses, not newly drawn X1 frames. Both facing directions and firing transitions have native presented-frame captures. Neutral jump, dash, wall and ladder artwork still has the cannon extended and needs further work. |
| X arrival | Uses the native arrival graphic transition for the supplied beam/energy art, then stands upright while the original controller finishes. The animation-phase byte stays zero during arrival; using it previously held a crouched tile. Both player slots have full presented-frame arrival captures. Exact SNES teleport timing/art is not implemented. |
| Zero damage, landing and arrival | Uses available fallback poses; the existing damage rectangles are not a qualified recoil animation. Landing uses the grounded idle/fire pose. Matching recoil, landing and full teleport sequences still need implementation and visual review. |
| Charge cue | The incorrect green projectile-impact overlay is removed. The replacement body pulses while the native charge state is active. This is an approximation; exact SNES charge colors, effects and timing are not implemented. |
| Projectile art | Native X4 normal/medium/full buster classes use supplied size-specific frames. Complete animated flight, muzzle and impact sequences and exact X1 Zero shot behavior are not implemented. |
| Movement and damage | Uses X4 movement, collision, charge thresholds and damage. Exact SNES X1 speed, acceleration, wall handling and damage tables are not ported. X4 boss weapons remain available to X by owner choice. |
| Zero's abilities | A playable buster interpretation; X1 Zero was an NPC. No saber, learned saber techniques, air dash or double jump. |
| Scripted/vehicle poses | Dedicated ride, door, arrival, death and stage-specific sprite coverage is incomplete. Generic available poses are not a claim of faithful bespoke animation. |
| Menus and story | Original X4 portraits, dialogue, movies and native menu artwork remain. |
| Host/rendering coverage | OpenGL on Windows only so far. Other renderers/platforms and netplay are unqualified. |
| Campaign coverage | Selected native combat, controls and current-build snapshots pass; complete stage/boss/route coverage and native-save progression are not qualified. |

The standing-fire correction and charge cue must be inspected for both seats,
both campaign rosters and both facing directions before another owner handoff.
Frame-matched RAM records the native controller state; the normal front/back
buffer delay can leave the first firing frame showing the preceding idle pose.
Inspect the whole transition instead of approving only the first RAM match.
