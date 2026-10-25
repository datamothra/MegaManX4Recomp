# Centered three-player split

The three-seat layout in Four Player Co-op now uses three 4:3 panes on its
existing 8:6 canvas. P1 and P2 occupy the top row; P3 is centered below them,
with black pillars on either side. Four-player play retains its 2x2 grid.
This work belongs only to the experimental feature branches.

The framework captures exactly three restored draw-only views and publishes
them atomically. Shared menus, movies, and unavailable-private-view fallback
use the same three-pane placement and fresh canonical images. P3 no longer
uses two half-captures, a wider placement/culling area, or special menu/HUD
offsets. All seats use the same native-width world and personal-menu draw.

Validation on 2026-10-24:

- `local_multiplayer_layout_test`: passed native and odd-sized canvas
  placement, centered P3 pillars, unchanged two-player and four-player geometry.
- `render_pass_sandbox_test`: passed exactly three captures from one common
  checkpoint, each declined seat, third-seat capture failure, complete-frame
  retention, simulation restoration, offline-only refusal, and recovery.
- `render_pass_abort_test`: passed third-seat watchdog unwind, restored live
  state and closed local-view scope, complete-frame retention, and recovery;
  existing pair and fourth-seat watchdog regressions also passed.
- Production compiler flags: both `gpu_gl_renderer.c` and
  `mmx4_coop_plugin.c` passed syntax checking with debug tools disabled.

These checks use the real render-pass transaction code with a mock presenter.
Live game rendering, pane screenshots, pause/resume, resized-window visuals,
and four-player gameplay remain pending integration QA. Earlier wide-bottom
three-player screenshots and reports document the previous layout only.
