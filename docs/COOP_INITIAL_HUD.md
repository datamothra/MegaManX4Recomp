# Independent HUDs during stage arrival

Tracked by `beads-eio.9.246`, 2026-10-25.

With X as P1 and Zero as P2, Zero finishes his native entrance before X.
Ending the paired arrival phase at that point briefly disables the private
camera passes while P1 still owns the native arrival lock. The shared draw
then puts both stacked meters into each Split pane. The original build
showed this for 26 presented frames during an input-only Intro stage start.

Keep the existing arrival phase until both native player controllers leave
their beam animation. This follows X5's principle that arrival presentation
must cover the paired entrance. Each native controller still advances once;
P1 retains ownership of the shared unlock. No extra simulation pass, new
option or serialized field is needed. Ordinary script and fade gates remain.

The Split and Side by side 8:3 choices also lose their Experimental label,
as requested by the owner. Their stored values and defaults are unchanged.

## Qualification

Runtime fix: `384ffe535a884d0d0efacd94d00012f208f4c8ca`, based on stable
`d68a03a4d01f1f1901dd77d48efe2a2990980ef2`. Framework:
`a251a98616f0c8f9e45c90c7ca71d20da71b8b21`. Windows Clang Release
ENHANCED/LLE instrumented QA executable SHA-256:
`1ea4a4c6893d5ed7de7c8e76c8e39158894d31c9e45e60cf4e15f34caa1e7097`.

Each startup observation retains 600 actual composed presentation images,
including the first visible health meters. Pixel checks inspect the native
health-fill columns for a second meter in each private view. These are
presented-image histories, rather than screenshots taken only after arrival.

| Case | Images with visible meters | Images with stacked meters |
|---|---:|---:|
| Original local Split, X / Zero | 131 | 26 |
| Original local Split, Zero / X | 127 | 0 |
| Fixed local Split, X / Zero | 126 | 0 |
| Fixed local Split, Zero / X | 133 | 0 |
| Fixed local Split, team death and retry | 250 | 0 |
| Fixed LAN independent view, P1 | 137 | 0 |
| Fixed LAN independent view, P2 | 261 | 0 |

Boots use native controller input. Only the offline retry setup moves both
players below the stage; native death processing consumes one team life
(`2 -> 1`) and performs the restart. No health or success flags are forced.
Local Split restore checks total 254, 264 and 504 for the fixed X-first,
Zero-first and retry runs respectively, with zero mismatches, aborts,
watchdogs or VRAM leaks. Unified also reaches playable gameplay with its
intended shared, stacked HUD; it does not use private render transactions.

Two real delay-LAN peers use the same binary and normal compatibility
checks. Independent movement and attack inputs pass, with 105 matching
core/mod CRC samples through tick 3360 and zero render mismatches or aborts.
This does not establish cross-build, cross-platform or Internet qualification.

The lifecycle regression fails on the original code and passes with the fix.
It exercises both campaign characters, both animation completion orders,
clearing P1's entry marker before his beam finishes, geometry waits and
checkpoint return. All 39 CTests pass. The lifecycle model also passes after
carrying the fix to the separate Four Player branch. The extra-player engine
uses its own arrival and presentation path; this is not new 3P/4P native QA.

Evidence and capture scripts are retained under
`G:/Temp/Codex/psxrecomp/x4-initial-hud`, including the original and fixed
image histories, RAM observations, numerical meter rows and netplay report.
This is a bounded Intro arrival/retry check, not a full-stage campaign audit.
