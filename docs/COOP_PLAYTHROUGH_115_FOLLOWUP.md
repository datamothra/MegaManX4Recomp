# Stable playthrough follow-up

Owner report, October 28, 2026:
[complete playthrough](https://youtu.be/ucIsvq2lM3k), supplied
`1.0.5 test playthrough.zip`. The archive's session metadata identifies
**1.0.15**, local 8:3 Split, Both-player doors and the X campaign.
Its SHA256 is `d170e582e6a652a8a24ad712acb03075c2d66bbfe3f4b253282bcdce54de4f2e`.
The original archive, cards and settings are preserved.

Additional feedback provides Web Spider air-dash examples at
https://youtu.be/kFoOg9fXX2w and https://youtu.be/k_uU8-exp5A, plus
`E:/Downloads/Boss door player 2 air dash of death bug 1.0.15.zip`
(SHA256 `53f2c8d087bd46b637bc32361e64ec787dd393dfab35e8dffb7507b380d2c067`).
Its trace identifies P2's 21-to-zero HP transition at native frame 15991,
stage 1/section 1, position 4295/1411: the outer boss door. This is an
additional admission case for `beads-eio.9.272`. The reported vertical
camera difference is being checked with that traversal. Bounded current and
unfixed-baseline Web air-dash controls both pass both doors and the fight
introduction, with camera Y 1280 in both views. Consequently that short
control does not reproduce the new report and does not prove it fixed.
The original public-build recording is being replayed with its state checks.

The owner also reports flying enemies swarming in during solo intro play
but failing to appear in two-player co-op (`beads-eio.9.276`). Neither short
clip depicts the intro; exact swarm location and reproduction are pending.
Current part 2 controls show all three P2-led flying groups. A P1-led group
is allocated but remains hidden when the check stops at X3066; continuing
the actual approach makes those same allocated actors drawable. This is a
test approach correction, not a new spawn or AI fix. The owner report stays
open until its exact location and traversal are reproduced.

This work is based on stable `c404f1d`, with framework `9868d30` and UI
`b964eab`. X1 replacements and Four Player Co-op are separate work.

| Report | Owning Bead | Correction |
| --- | --- | --- |
| P2 air-dash death at Cyber Peacock's inner door | `beads-eio.9.272` | Apply the admitted passenger's native door collision suspension even when airborne. |
| P2 starts Dragoon's fight and the camera remains enclosed | `beads-eio.9.273` | Retain the native main-fight camera release before restoring the projected owner. |
| P1 dead, P2 defeats final Sigma and cannot progress | `beads-eio.9.274` | Retain the victory camera release and give the ending controller the surviving entrant. |
| Web Spider's corridor scenery follows P2 into the arena | `beads-eio.9.275` | Continue each independent view's native background parallax during a paired door. |

## Native causes

Cyber Peacock's airborne admission retains `PLAYER+67 = FF`. The existing
Both-door passenger handler excluded that state, leaving its terrain box
active while the shared door moved it through a still-sealed wall. The
original crush bits changed to `13` and full-health P2 died at approximately
967/2485. Removing that exclusion applies the same native `C1C24` null-box
setup already used for grounded participants. Admission, movement, animation
updates, door timing and damage remain native; no immunity is added.

Dragoon's `7E3D0` releases its script before `7E400..7E430` writes the room
targets and follow speed. A P2 projection could restore the closed
5264..5264 enclosure over those writes. Extend the existing refight release
publication to the main fight's 5264..5104 targets and follow step 4. Only
matching closed views in the same vertical room receive those authored
targets; origins, current bounds and easing remain independent.

Final Sigma has the same ordering at `8F884`: `36B18` releases the scene
before `8F8C4..8F8D8` writes max 1152/min 1104. Publishing that completed
release prevents stale 1104..1104 shadows from trapping the survivor at
1416.5. There is a second gate: ending controller `D3048` reaches `D2B9C`,
which tests the singleton player's X against 1761. A dead P1 remains at 1127
in the upper arena while P2 reaches the exit. Reuse the existing scene-actor
ownership wrapper for that complete controller, scoped to stage 12/section 1.
It retains the entrant through camera wait, dialogue and native completion,
while preserving the original campaign identity. Both developer and public
configs emit the hook. Regeneration changes one game shard; no framework
change is required.

Web Spider's `D8ED4` selects the region and `D9138` manually advances mode 5
background parallax. Paired doors keep independent cameras, but the
background handler treated them as complete shared-camera scenes and skipped
private updates. P2's background X remained 4352 while its foreground moved
4376..4623, requiring background 4394..4578. Exempt paired doors from that
shortcut. Each saved view retains its own region phase and native parallax;
the canonical controller still updates once. Ordinary shared scenes still
reset private region initialization as before.

## Bounded qualification

`tools/coop_playthrough115_scenarios.py` provides `cyber_air_door`, `spider_air_door`,
`magma_entry_camera`, `spider_door_scenery` and `sigma_survivor_victory`.
Run them through `tools/test_mmx4_coop_regressions.py` with an original USA
disc and a development build. Use `--boss-doors both --cameras split
--local-cameras split --hidden-window`; use a fresh output
directory and unoccupied debug port for each run. Repeat with campaigns 0/1
to exchange the native heroes. Put Sigma last because it leaves gameplay.
Normal boot is used for the latest Web checks; two accelerated startup
attempts stalled in the BIOS before entering that scenario and are excluded.

Door checks use native input for admission, actual closing, boss introduction
and control recovery. Cyber's air dash prerequisites are prepared as learned
Jet Stingray ability only (Zero) or native foot armor (X); Cyber's clear flag
remains unset and damage remains enabled. Recorded native action 13 confirms
an actual air dash. The Spider check compares each
view's background with the original parallax formula during crossing.
Dragoon tests either entry leader. The existing `door_animation` case checks
ground walking/dashing, once-per-update animation and scripted movement.

Sigma prepares one HP on the currently selected live health pool, then
requires actual attacks against each native damage rectangle. The first
head's death returns the actor to combat; only the final victory scene counts
as defeating both. P1 remains dead through the native drop, final defeat,
dialogue and ending approach. No result flags or scene phases are supplied.
Protection prevents incidental combat damage but leaves native lethal terrain
active; movement up the final exit steps and ending admission use real input.
The final Sigma ending handoff currently passes native qualification with
X as P2. Zero's extra combat automation is unqualified: a short melee setup
entered lethal suction terrain, and a safe-ground Ryuenjin attempt preserved
health but did not connect defeating hits within its bound. Neither attempt
reached the victory scene or establishes an ending failure. Both campaigns'
ending-owner projection is covered by lifecycle units. Full ending movie and
credits playback are not claimed.

The reduced QA observer makes six RAM reads per sample instead of eleven,
and caches the fixed profile's diagnostic address. Its fields match the old
observer across 24 static fixtures (`observer-parity.json`). It does not
change runtime pacing or the game's update rate. Native text confirmation
prefers the body carrying the script marker when both heroes remain visible.

The current runtime passes all 43 CTests. Native qualification on executable
SHA256 `ecbd879844d869e48aa68e73705afc926799c858a692f0d149f4ea8c520265cf`:

| Check | Evidence | Result |
| --- | --- | --- |
| Cyber inner-door genuine air dash; actual closing, boss introduction and controls | `zero-native`, `native-final-1` | Both P2 hero choices pass, damage enabled. |
| Dragoon first-visit introduction and native camera pan | `native-final-0`, `native-final-1` | Both heroes and both entry leaders pass; actual origins reach 5149. |
| Web paired-door background parallax and fight recovery | `zero-native`, `native-final-1` | Both P2 hero choices pass; 19/20 crossing observations. |
| Sigma upper phases, both final health pools and survivor ending handoff | `sigma-qualified-1` | P2 X passes; P2 Zero remains unqualified as explained above. |
| Additional Web outer air dash | `web-air-and-bees`, `web-bee-approach` | Passes, but also passes unfixed baseline; exact reported death remains open. |
| Intro part 2 source group at 3167/3296 | `web-bee-approach` | P1 native allocation plus closer approach/drawing pass; no game fix claimed. |

The extra legacy `door_animation` run in `native-final-1` passes complete
grounded walking, scripted carry and independent control recovery. Ground
dash opening/carry/closing checks pass, but the renderer diagnostic run hits
the existing starvation watchdog during its boss introduction. It is not
counted as a complete dash pass. Previous stable release qualification is
retained; no watchdog or guest timing setting was weakened here.

Private evidence is under
`G:/Temp/Codex/psxrecomp/x4-playthrough115/`. Baseline reproductions are
`cyber-baseline-0`, `magma-baseline-probe`, `spider-baseline` and
`sigma-native-victory-geometry`. Rejected early Sigma attack fixtures and
premature post-intro waits are retained as failed setup attempts, not passes.
Final qualification results and binary identities are recorded separately in
that directory. These bounded local checks do not establish a fresh full-game
playthrough, LAN qualification, or Four Player coverage.
