# Audited native frame wait

SLUS-00561's complete 156-byte SDK routine at `0x800E4EF8` matches the
qualified Tomba caller after relocating its paired frame counter, warning
string, three callbacks and internal jump. It polls `0x8011DC50`; audited
edges are `0x800E4F20` and `0x800E4F6C`. Timeout callbacks remain
`0x800EDC74`, `0x800EDE8C` and `0x800EDE9C`.

Enhanced builds select portable native induction. Reference builds retain
original polling. Existing netplay/precise exclusions remain. The actual
regenerated routine is checked by `mmx4_vwait_contract`.

The framework pin backports the existing audited store-counter implementation
and campaign binding onto X4's prior framework lineage. This preserves its
host snapshot/guard, co-op, language and GL batch/atlas contracts. It does not
move X4 to the distinct X6 bridge package. Optional scaled-charge batching
stays off, with its selected value recorded in compatibility identity.

This is a repository PR only: no new X4 release or quantified performance
claim. Central evidence is tracked in `beads-x79c` and campaign `beads-2wy8.1`.
