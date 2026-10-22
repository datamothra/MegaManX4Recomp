# Playing and reporting co-op

Use the same [release](https://github.com/mstan/MegaManX4Recomp/releases)
on both computers. The launcher and netplay UI are included on Windows and Linux.

## Local co-op

In Mods, enable **X + Zero Co-op** and start a fresh game boot. Keep OpenGL
selected. Controls has assignments for both players: choose different physical
controllers, even if they are the same model, or configure separate keyboard
bindings. The game uses digital PlayStation controls.

Player 1 owns the campaign. Player 2 uses the other character; boss clears and
permanent upgrades follow P1's campaign. Lives represent team retries. A dead
partner waits for the team's retry. Either living player can use Select in
the pause menu to Quit, including P2 while P1 is dead.

Unified cameras are the local default; Local co-op display also offers experimental
side by side 8:3. HUD layout can be Stacked or Side by side.
With Independent pause menus enabled (the default), either player's Start/Options
binding opens both heroes' native menus. Each player manages their own weapons,
techniques and E-tank energy; either player resumes after healing finishes.
Gameplay pauses for both players. The player who opens Quit controls its
two confirmation pages. Either living player can also select Escape when
the native cleared-stage rules allow it. Options remains controlled by P1.

## Netplay

Press **Netplay** in the launcher and select the **X + Zero Co-op** profile.
LAN / Direct IP requires no account; Online Netplay uses the lobby's Discord
sign-in. Both players need their own matching USA disc and the same release.
Two players are supported. Online startup reports remain open; this release's
camera validation used LAN peers.

The host chooses Unified or experimental Split cameras and the shared co-op
options. Split gives each peer a separate view of the same simulation; health
pickups refill the collector without pausing the other player. Unified keeps
the native refill pause. Genuine scene changes still carry living partners
through their teleport animations.

## Optional settings

In the local launcher's **Mods** page, select **X + Zero Co-op** to open these
settings in the right-hand panel. They work in local co-op as well as netplay;
only **Netplay cameras** is online-only. Changes apply on the next fresh boot.

- **Boss doors and refight teleporters:** Either player is the default. Both
  players waits for both living, present characters to touch the same door or
  fortress refight pad; dead or withdrawn partners are exempt.
- **Fight Double and Iris:** off by default. Fight the campaign's usual boss,
  return through the inner door for the other encounter, then continue P1's story.
- **Separate E-tank contents:** off by default. Both heroes use the tanks acquired
  by P1's campaign, with their own energy when enabled. Pickups refill the
  collector's supply and each hero uses their own energy in their pause menu.
  W-tank energy remains shared. P2's contents persist for the session and in save
  states; P2 does not gain a separate campaign save. Requires a fresh boot.
- **Co-op boss scaling:** off by default. Double effective health and 20% less
  boss damage from Zero. Its default **Separate per-player cooldowns** lets each
  hero damage independently, with short recovery for Zero's ground and aerial
  slashes. **Reduced shared cooldowns** uses one shared timer. Both methods shorten
  native hit cooldowns; the damage reduction applies with either method.
- **Ultimate Armor X Code / Black Zero:** off by default and compatible with
  each other. X's code makes a capsule grant Ultimate Armor; it does not grant
  the armor immediately. Both codes are available under **X + Zero Co-op** for
  local and online play. The standalone Mods also work in single-player.

## Saves and rewind

Use the game's normal memory-card saves for campaign progress. Co-op uses an
isolated save profile. The launcher's memory-card settings show the active
location; changing it does not relocate diagnostic recordings.

Offline save-state controls use your configured PlayStation button bindings:

| Action | Control |
| --- | --- |
| Open save states | F7 |
| Choose a slot | Left / Right |
| Save | Square |
| Load | Cross |
| Back | Circle |
| Open rewind | F8, with Rewind enabled |
| Browse rewind / accept / back | Left / Right, Cross, Circle |

Save states and rewind are unavailable during a netplay match. Use states made
with the same release. HUD layout and native character-code choices can change;
mods that change memory layout or an ongoing co-op/boss protocol still need to
match. With diagnostic recording enabled, loading a state or rewinding starts a
new diagnostic session with a `baseline.pst` file.

## Send a useful bug report

1. Enable **Mods → Playtest Diagnostics → Input Display and Recording** before
   local play. For netplay, the host enables **X + Zero Co-op → Netplay diagnostic
   recording** for both peers before starting the match. Both default off. The
   input display shows P1/P2's accepted buttons and **REC** while recording.
   Existing explicit recording preferences are preserved when updating.
2. Reproduce the problem and note the stage, which player led, and the
   approximate video timestamp. New recordings identify the release and
   effective play/camera mode automatically; include those manually for older
   recordings that do not have this metadata.
3. Quit normally. Open **`saves/diagnostics` beside the executable or AppImage**.
   `diagnostics-location.txt` beside the application names the session folder;
   `startup-log-location.txt` names the latest startup log.
4. Zip the full session folder, including inputs, metadata, settings, mod
   choices, starting cards/absence markers and any `baseline.pst`. For a startup
   failure, include the newest `startup-*.log`. Collect both peers for netplay.

Recordings include copies of your starting game saves. Send the whole folder
with your video and release version, not just `metadata.json` or an empty
memory-card directory. If no recording appears, send the location-file error
and startup log. The AppImage writes diagnostics outside its temporary mount.

New `session.json` metadata includes `game_version`, `initial_mode` and the
committed co-op options. Camera labels distinguish `local_unified`,
`local_split_8_3`, `netplay_unified` and `netplay_separate`; disabled co-op is
`single_player`. `mode-changes.csv` records changes at their native input and
game-frame boundaries, including campaign changes and partner initialization.
It is written by the background recorder and does not change the replay input
format. Include it when sending the full session folder.

Local recordings support offline replay with the matching build and assets
using [replay_mmx4_diagnostics.py](../tools/replay_mmx4_diagnostics.py).
Netplay traces support diagnosis; full netplay replay is not currently supported.

Recording uses a bounded background writer for checksums and input-file writes.
It flushes about every 100 ms, including while the game is paused, and drains
accepted inputs on normal exit. An abrupt process kill can lose the unflushed
tail. If storage cannot keep up or a write fails, the display changes to
**ERROR** and `diagnostics-location.txt` records the cause; capture stops
without silently skipping inputs. Paths and the replay format are unchanged.

Ordinary Linux settings and cards live under `~/.local/share/MegaManX4Recomp`
unless overridden with `MMX4_RECOMP_DATA_DIR`; diagnostic recordings remain
beside the AppImage. Avoid placing the application in a read-only folder.
