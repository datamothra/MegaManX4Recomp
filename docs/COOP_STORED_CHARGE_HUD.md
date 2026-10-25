# X armor stored-charge HUD ownership

The charged-shot stock icons below X's health bar are personal HUD artwork.
They must follow the X that owns those stored charges, and must never appear
below Zero's health bar. This applies to both campaign characters, local Split
and Unified, and independent online cameras.

## Original executable evidence

The supported SLUS-00561 executable creates a shared particle of type `0x36`
only for X at `80035558..80035584`. Its deferred updater is `800B2C8C`:

- Initialization at `800B2CA0..800B2CE8` sets screen-relative layer `FF`,
  coordinates `(32,52)`, CLUT `780A`, and the current character's assembly
  member at `SCRATCH+1C` plus `30`.
- `800B2CEC..800B2D3C` hides the actor when the native HUD is hidden or
  `PLAYER+A6` is zero, otherwise it uses frame `31 - PLAYER+A6`.
- The particle belongs to the shared `80173CA0..801754A0` pool, with stride
  `60`, drawn by the world loop at `800240D0..800240F4`.

It is outside the native health-HUD routine `80024E70`. Therefore redrawing
the shared world for another Split camera also redrew X's icons under that
view's own health bar. When P1 was Zero, the deferred controller additionally
read Zero's counter and character resources instead of the allocating X's.

## Fix

Reuse the existing snapshotted particle allocation owner. Run a P2-owned stock
controller with P2's projected native context. At draw time, admit the actor
only into its owner's private HUD, or apply the same offset as that player's
health group in Unified. Resolve the original X artwork through the immutable
UI bank and retain its left HUD anchor. Restore temporary draw coordinates and
contexts before returning. No charge counter, gameplay body or native code is
patched, and private views do not advance the controller.

The two-player correctness change is independent of the experimental
four-player mod. On the feature branch, the four-player engine separately
tracks all 64 particle slots with a 1-based allocating seat, resets ownership
on allocation/stage initialization, and includes it in its synchronized
digest. Each X variant's controller uses that seat's context and each private
view draws only its own stock display. This works with the centered
three-player presenter, whose draw callbacks are exactly seats 0, 1 and 2.

## Validation

The strict Clang combat boundary suite covers X as P2 with four and zero
stored charges, canonical Zero isolation, unchanged player/charge bytes,
private-view refusal, allocation reuse, and actor-pool bounds. Native visual
and replay qualification is recorded separately when performed; these boundary
tests alone do not establish that a gameplay image is correct.

The supplied recording (`Charged shots hud display bug.zip`, session
`1792889506553145`) was replayed with its exact original preview binary.
All 16,902 inputs in the bounded photo-near prefix verified. A read-only
2 MiB RAM capture at completion shows X with `PLAYER+A6=4` and the live
controller at `80173CA0`: type54, visible, layer255, position32/52,
CLUT780A, frame27. This confirms that the reported icons are this controller.
It establishes the original reproduction and actor identity, not a pass for
the modified build.

Both development and release recompiler hook lists include `800B2C8C`;
regenerate the native code before testing this updater interception.
