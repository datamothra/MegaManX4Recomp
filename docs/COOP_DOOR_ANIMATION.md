# Both-player door animation polish

Local base-branch follow-up to X5 commit `3e6173c`, tracked by
`beads-eio.9.270`. Current review branch: `review/door-animation-current`,
based on master `79e38d84fe971cc3c186fd451913fa4ab639893f`.
The original native qualification used stable 1.0.14,
`3656e01304519732fb9736c7a0b1847f9139038a`.
X1 and four-player changes remain on their separate feature branches.

X4's Both mode already allows independent movement after a door opens.
That free-traversal path remains intact. During the preceding opening lock,
the passenger's neutral steering can select a stop/dash-end pose, then both
heroes remain frozen on their current animation frames for 76 game updates.

The original US executable identifies the relevant native paths:

- `800311EC` runs each body once. `800312B4` branches past action dispatch
  when `PLAY+10` is set, suspending its usual animation advance.
- `800338CC` initializes door action 19 and preserves a running/dashing
  program, or chooses automatic-walk program `26` from idle/jump poses.
- `800350A4` selects native artwork/animation resources. It does not advance
  movement, contacts, the shared door controller or shared clocks.
- `80015DC8` is the animation leaf: decrement byte `44`; on expiration,
  advance cursor `34` by signed byte `46` times four and load bytes `44..47`.

The existing body filter now preserves the passenger's incoming native run
or dash program around its original neutral-steering body call. Waiting
idle/release poses receive the corresponding native automatic walk/run or
dash program after that body call. During the shared opening lock, it calls
only the animation leaf once per eligible on-foot body update. The original
body/physics pass still runs once, with its existing input; opening/closing,
admission, cameras, collision boxes and progression retain their owners.
Hitstop, hidden/dead heroes, mounts, other scenes and local render passes are
excluded. Free movement after opening resumes its ordinary animation path.
No hook site, serialized field or setting was added.

## Bounded qualification

Evidence: `G:/Temp/Codex/psxrecomp/x4-door-animation`.
Final qualification results are recorded in `qualification.json` there.

The `door_animation` scenario uses Jungle part 2's authored boss checkpoint.
It approaches the real common type-8 door by controller input, walking and
dashing, then observes actual opening, closing, Web Spider's introduction,
full boss HP and independent controller jumps after release. Fixtures select
the checkpoint and prepare positions only; final runs retain actual damage
and deaths. No door phase, animation, timer, camera result, boss HP or scene
completion is written by a fixture.

Presented-frame RAM records both bodies, PLAY and the actual door. Each
consecutive locked update checks the original animation leaf's cursor/timer
transition, the retained run/dash program and unchanged body positions. The
same scenario reverses campaign roles to cover both X and Zero as passenger
and opener. Composed images and render-pass verification complement the RAM
checks; heroes can overlap at the admission box, limiting visibility of some
individual sprite parts. Only one common door mechanic is added as a case.

```powershell
python tools/test_mmx4_coop_regressions.py `
  --exe <development-build>/MegaManX4Recomp.exe `
  --bios <development-build>/bios/openbios.bin `
  --disc <original-USA-disc.cue> --game game.toml `
  --output <new-private-directory> --hidden-window --quick-boot `
  --boss-doors both --cameras split --local-cameras split `
  --campaign 0 --cases door_animation
```

Repeat with `--campaign 1`. The existing admission-policy checks remain
available as `--cases boss_door_policy`; no duplicate stage matrix is added
for doors using the same controller. Mounted admission, every stage-specific
door, other hosts and LAN have not been newly qualified by this polish.

Local human review: `owner-review/Try Door Animation.cmd` in the evidence
directory. It verifies the candidate identity, boots to the original checkpoint
and prepares a current-build paused approach for P1 keyboard/P2 DualSense,
with normal audio and a normal window. It preserves the private profile's
cards and uses slot9 reserved for this review. It leaves an active X1 playtest
running and asks the owner to finish that window before starting this one.

The review panel provides Walk and Dash checks, an immediate Restart approach
button, and per-binary Pass/Fail/Deferred notes. It reads actual SIO samples
while paused: tap keyboard Right, release, then DualSense Right to verify
independent input ownership. Configured device IDs alone do not count as a
passing control check. Notes remain in `owner-review/door-review-notes.json`;
individual failures and deferred items must be read before merge.

Unpause with Enter/Options, move both heroes right, and use S/Circle to dash.
Observe native opening animations, actual closing, the boss introduction and
independent jumps after control returns. The setup does not complete any of
those results. Both approaches restore the same pre-door snapshot; their
different inputs exercise walk/run versus dash without adding duplicate
stage-mechanic cases. The owner requested approval before merging this local
branch into master; the review setup does not publish or merge it.

Original Windows qualification: **42/42 CTests passed**, plus all four native
walk/dash routes across both campaign rosters, with damage enabled. Opening
remained **76 updates**, matching baseline. **592 consecutive animation
cursor/timer checks** passed across the suspended body passes, with
**11844 render checks** and no mismatch, VRAM leak, abort or watchdog.
The lock is asserted after that update's body passes; the following update is
the first suspended body pass. The observer excludes that assertion boundary
from its once-per-update comparisons, avoiding an extra animation tick.

Current-master review rebuild: **43/43 CTests passed**, including the actual
regenerated native-wait caller contract. The door implementation is unchanged
from the qualified native runs above. Current-build human door checks and
physical control ownership remain pending in the new review panel; the old
runtime qualification is retained as historical evidence, not a claim that
the rebuilt candidate has already received the owner's play check.
