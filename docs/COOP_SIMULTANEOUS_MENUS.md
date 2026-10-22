# Independent co-op pause menus

Requested October 20, after Playtest 42. Item 209, `beads-eio.9.207`.
Included in Playtest 43 through [PR #54](https://github.com/mstan/MegaManX4Recomp/pull/54).

The co-op option **Independent pause menus** defaults on. Either living,
present character can pause. Both character menus open; each controller
navigates its own native menu, weapon selection and E-tank contents. Either
living character can resume the team. The campaign, acquired upgrades and
save data still belong to P1.

Local co-op displays two menus side by side, including when gameplay uses a
Unified camera. Local 8:3 keeps its paired canvas. Each netplay peer displays
its own character menu in both Unified and Split. Menu drawing is a private
render transaction; it never advances gameplay or tank consumption.

While this option is on, E-tank contents are always private. The existing
E-tank checkbox is explicitly a preference for the older, one-menu-at-a-time
mode and cannot turn off this requirement. Switching independent menus off
restores that preference without rewriting it. W-tank energy remains shared.
Both the option and effective E-tank policy are recorded in diagnostics;
the option enters the native match configuration and source compatibility ID.

Tank use blocks unpause while the partner keeps navigating and confirming
equipment. Options remains usable, and healing continues behind the shared
Options/Quit frontend. Escape and Quit cannot leave the menu during healing.
Requests on the same frame are deterministic: tank confirmation takes priority
over resume; simultaneous tank requests start P1's operation first. A second
tank cannot start until the first finishes, including the shared W-tank.
Blocked exit and tank requests are consumed, requiring a fresh press after
completion; holding Start through healing never resumes gameplay afterward.

Dead or withdrawn players cannot use a tank, change equipment or resume.
Their native menu can still be shown. Either living player can press Select
to open the shared Quit frontend and control both native confirmations; the
other controller cannot confirm or cancel it. Either can select Escape when
the native cleared-stage rules permit it. Both actions use one shared native
exit transition, including with P1 dead. Options remains controlled by P1.
Shared frontends block personal input and team resume.
Start closes P1's native Options page first; another fresh press is required
to resume gameplay. Options/Quit pages never draw a partner world sprite.
Native fades, sound transitions and the resume world update run once.
Both personal views replay the native fade's existing shade; private draws
never advance its task. Menu graphics stop uploading before gameplay palette
restoration, and the presenter switches to world drawing at the native fade-in
phase. Local Unified changes back from two menus to its shared view while
black; local 8:3 keeps its two views throughout the return.
Only living characters apply native equipment changes on exit. Stage resets
retire both menus and their guards. Both personal menu records, their original
weapon selections, inventories and input history participate in snapshots and
deterministic state digests. Older snapshot layouts are rejected.

Boundary qualification passes the two rosters, either opener,
shared/split models, equipment changes during healing, healing priority,
no held-input resume, private contents, shared-W request serialization,
snapshot restoration, guest restrictions and surviving-player resume. The
focused Windows CTests pass, including catalog defaults and emitted hooks.
The Linux production build and all 30 CTests pass. Current lifecycle,
diagnostics and catalog checks also pass on Windows.

Original-disc native checks use controller input for all menu actions;
fixtures only prepare the stage, damage and supplies. No fixture selects a
weapon, heals a character, moves a cursor or dismisses a menu.

| Mode | Campaign | Native qualification |
|---|---|---|
| Local 8:3 | X, with Zero as P2 | Independent management, healing locks, both resume directions, paused snapshot restoration, selected weapon firing, shared confirmations and dead-P1 management pass. |
| Local Unified | Zero, with X as P2 | The same checks pass with the characters reversed. |
| Split LAN | X, with Zero as P2 | Independent management, healing locks, shared confirmations, surviving P2 and matching authoritative core/mod CRCs pass on both peers. |
| Unified LAN | Zero, with X as P2 | The same checks pass with the characters reversed. |

A further Local Unified run prepares only 32 HP of tank energy per seat and
heals 48 HP across the team. That exceeds a shared pool and verifies the
required private contents with the separate-tank preference off. Its 2,756
render verification checks pass without mismatches or aborted draws.

The healing-input refinement passes a fresh Local 8:3 controller run: X
changes weapon while Zero is still healing, returns to Lightning Web, holds
Start past completion, then resumes with a new press. Its 3,158 render checks
pass. A separate native Unified run opens P1's Options during P2's E-tank
use; P2's health rises from 4 to 9 under that frontend and reaches 32 before
resuming. All 298 render checks pass, and its Options capture is clean.
The same live equipment/held-Start check passes Unified LAN with X as P2
and Zero as P1; both peers retain matching authoritative core/mod checksums.
The LAN harness holds each chord for six frames so it crosses the configured
input delay before observation. Its initial two-frame observation failed to
see the change; that attempt is retained and is not counted as a pass.

Owner QA accepted menu management, but reported an abrupt, artifacted return.
Before/after native frame captures reproduce the missing private fade: the
old menus remain bright throughout the exit, including the gameplay fade-in.
The corrected Local 8:3 and Unified captures show menu fade-out, a black
palette/layout handoff, then a clean stage fade-in. The current lifecycle test
covers both frame buffers' displayed shades, the black restoration boundary,
no late menu uploads and exactly one shared world update. Windows focused
checks and all 30 Linux CTests pass after the change.
A fresh Split LAN run with Zero as P1 also passes healing, independent
equipment, both resume directions and render restoration; both peers retain
matching authoritative checksums. These checks qualify identical private
Linux artifacts, not cross-OS matchmaking.

Composed screenshots were inspected for both character menus and shared
frontends, including a clean Options page after suppressing the stray P2
sprite. `PSX_RENDER_PASS_VERIFY=1` remains enabled: the native checks require
zero restoration mismatches, aborted passes, watchdogs or leaked VRAM writes.
Immutable menu textures and palettes use journalled renderer uploads inside
private draws; they do not stream GP0 payloads into authoritative CPU VRAM.
The broader GP0 upload-journal defect is tracked as `beads-eio.3.375`.

Evidence is retained under `build-pr23/paired-menu/` and
`/home/matthew/mmx4-paired-menus-20261020/`: `qa8` contains the local native
checks; `qa10` contains the final clean-Options check and both connected modes;
`qa11-energy-proof/runtime` records the limited-energy proof above.
`qa12-tank-navigation/local-split-0` records live equipment management during
healing; `qa13-options-tank/runtime` records healing under Options.
`qa14-tank-lan/netplay-unified-1` records the final connected recheck.
`qa15-exit-before/runtime/exit-frames` retains the old exit; its capture run
completed the native checks but failed its optional video encoding because
Linux FFmpeg was absent. `qa17-exit-fade/runtime` and
`qa18-exit-unified/runtime` retain the corrected 60-frame sequences and phase
logs, with clean render verification. `qa16` is an intermediate capture before
adding the missing fade overlay and is not the final qualification artifact.
`qa19-fade-lan/runtime` records the connected regression check.
The LAN runs qualify identical Linux development artifacts, not cross-build,
cross-OS or public-lobby compatibility. Windows full-runtime linking is being
checked separately; the Windows model/catalog results are not a claim of
native Windows gameplay qualification.

The generated output was regenerated for four new native hook entries and
then reproduced without changes by the pinned Linux emitter. Private QA
artifacts and startup attempts live under `build-pr23/paired-menu/`; those
inspection executables are not release or compatibility artifacts.
