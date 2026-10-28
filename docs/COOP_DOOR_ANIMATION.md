# Scripted Both-player door entry

Local base-X4 follow-up to X5 commit `3e6173c`, tracked by `beads-eio.9.270`.
Branch: `review/door-animation-current`, based on master
`79e38d84fe971cc3c186fd451913fa4ab639893f`. X1 and four-player work remain separate.

The owner rejected the previous preview's free traversal after opening.
Both-player mode must retain scripted control through entry, like the original
single-player game. Both living, present heroes still have to touch the same
door. After admission, releasing controls cannot stop the crossing, and steering,
jump, fire or dash input cannot take over until the door releases them.

## Native path and implementation

The original USA executable supplies these routines:

- `800338CC` consumes positive C4, keeps a run/dash animation (or selects native
  automatic walk `26`), faces right, sets action19 and changes C4 to FF.
- Action19 dispatches to `80032F64` / `80032FA4`. While C4 is set, it advances
  native animation leaf `80015DC8`, without ordinary player physics/steering.
- `800312B4` bypasses action dispatch while the shared opening lock PLAY+10 is
  active. Each suspended body receives only one animation-leaf advance per
  original body update. A passenger that reaches this pass after the door
  asserts the lock first runs native338CC to initialize its own action19.
  A run/dash release clip at admission selects its corresponding looping
  native run/dash clip once; later updates retain and advance that program.
- Native `800C1C24` disables the opening hero's terrain box; the companion keeps
  the same protection during entry. Native `800C1C88` ends opening and supplies
  the authored destination room bounds. Action19 and C4 remain in effect.
- `800C1D90` adds exactly `0xA400` fixed-point units to the original singleton's
  X once per door update. Its existing Both-player filter applies that same step
  to each living participant, retaining one shared controller update. Ordinary
  body actions own animation; no extra physics or movement pass is called.
- Completion waits until both full native foot boxes clear the aperture and
  the existing independent-camera destination interval is committed. The box
  offsets come from the same original tables that `80035EA4` restores. Both
  C4 flags and boxes are restored on release, or if the door aborts. The shared
  native closing animation, sound and following boss introduction each run once.

The former normal-control override, return-strip re-entry scan and open-door
map-wall exception are removed. The native scripted action already crosses
with its terrain box disabled. There are no new serialized fields, settings
or hook sites. Either-player admission, native cameras, opening/closing clocks,
other scenes, mounts and the rest of gameplay retain their existing owners.
The shared door releases at its native closing transition; the subsequent boss
introduction applies and releases its ordinary scene lock.

## Bounded qualification

Evidence: `G:/Temp/Codex/psxrecomp/x4-door-animation`.
Current scripted-entry results and source/binary identities are recorded in
`scripted-entry-qualification.json`. Earlier free-traversal qualification in
`qualification.json` is historical and does not clear this changed requirement.

The `door_animation` scenario selects Jungle part2's authored boss checkpoint
and prepares positions only. Walking admission is followed by neutral input;
dash admission is followed by held Left+Jump+Fire+Dash. Each run must observe the
actual opening, scripted displacement, native closing, Web Spider's introduction,
full boss HP and independent jumps after control returns. Both campaign rosters
exercise X and Zero in each seat. No door, animation, timer, camera result, boss HP
or scene-completion value is supplied by a fixture; damage remains enabled.

Completed-frame observations check animation cursor/timer transitions during
opening and traversal, action19, C4 and the original A400 movement step. Live
body records supply C4; the retained 128-byte per-frame body slice does not
include that offset. Render-pass verification and composed captures accompany
the native observations. Only one common door mechanic is added as a case.
Unit checks also cover opposing inputs, restored terrain boxes, missing/dead
participants, camera commitment, aborts and current-format snapshots.

```powershell
python tools/test_mmx4_coop_regressions.py `
  --exe <development-build>/MegaManX4Recomp.exe `
  --bios <development-build>/bios/openbios.bin `
  --disc <original-USA-disc.cue> --game game.toml `
  --output <new-private-directory> --hidden-window --quick-boot `
  --boss-doors both --cameras split --local-cameras split `
  --campaign 0 --cases door_animation
```

Repeat with `--campaign 1`. Mounted admission, all stage-specific doors,
other hosts and LAN are not newly qualified by this bounded check.

## Owner review

Run `owner-review/Try Door Animation.cmd`. It verifies the candidate identity,
boots a normal window with normal audio, prepares a fresh damage-enabled paused
approach, and assigns keyboard/P1 and DualSense/P2. Slot9 belongs to this review;
native cards and other settings/notes are preserved. An active X1 playtest is
left running until the owner closes it.

The panel provides Walk and Dash checks, Restart approach, and per-binary
Pass/Fail/Deferred notes. While paused, hold keyboard Right briefly, release,
then hold DualSense Right to verify actual independent SIO inputs. Configured
GUIDs alone do not count as passing ownership. Enter/Options resumes.

Move both heroes to the door, optionally using S/Circle to dash. Once opening
begins, release input or try to retreat/jump/fire. Both must finish entry under
scripted control, close the door and reach the real boss introduction. Confirm
that each can jump after control returns. Read `door-review-notes.json` before
follow-up, preserving individual failures/caveats. Merge only after the owner
approves the corrected candidate.
