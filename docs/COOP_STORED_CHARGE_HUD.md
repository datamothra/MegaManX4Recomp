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

This correctness change is independent of the experimental four-player mod.
Additional X seats need the feature branch's seat-aware ownership adaptation.

## Validation

The strict Clang combat boundary suite covers X as P2 with four and zero
stored charges, canonical Zero isolation, unchanged player/charge bytes,
private-view refusal, allocation reuse, and actor-pool bounds. Native visual
and replay qualification is recorded separately when performed; these boundary
tests alone do not establish that a gameplay image is correct.
