# X1 character replacement spike

Branch: `spike/x1-character-replacements`, based on stable `master` at
`06bb87f30f11d097469daa1e5de5db0687341971` (1.0.11). This branch does not
include the game's four-player co-op implementation.

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
| Windows CTest suite | 40/40 passed |
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
