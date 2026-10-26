"""Native yellow pad, pre-Sigma scene and forward-section regression.

Stage/checkpoint/health/position fixtures prepare the approach. The eight prior
refight clear bytes are explicitly bypassed prerequisites; this does not test
those fights. Pad admission, the NPC scene and forward transfer use native
controller input without writing their success flags or actor phases.
Zero's interstitial movie uses the original global pad1 Start skip; full movie
playback and a P2-only movie skip are outside this scene-entry qualification.
X can briefly use the same mode10 transition without playing that movie.
"""
import time
import struct


def sigma_entry(s):
    r = s.r
    cases = []
    for name in getattr(s, 'sigma_entry_cases', ('p2-survivor', 'p1-survivor', 'both', 'both-p2')):
        prefix = 'sigma-entry-' + name
        dead = 0 if name == 'p2-survivor' else 1 if name == 'p1-survivor' else None
        leader = 1 if dead == 0 or name == 'both-p2' else 0
        live = (leader,) if dead is not None else (0, 1)
        # A fresh native level load retires the preceding scene and deaths.
        r.fixture(5, 3)
        s.load(0, 0)
        s.load(12, 0)
        r.fixture(5, sum(1 << seat for seat in live))
        if dead is not None:
            r.fixture(2, dead, 0x80)
            s.wait(prefix + '-death', lambda row: row['players'][dead]['state'] == 3 and
                   row['players'][dead]['hp'] == 0, 15)

        # Native C78BC reads PLAY+26[8..15] before exposing the yellow pad.
        # Only these earlier-refight prerequisites are bypassed. No entrance,
        # scene, door, checkpoint or Sigma-defeat result is set here.
        for index in range(8):
            r.write(0x801721C0 + 0x2E + index, 1)
        # Do not use advance_dialogue during this arrival: its Jump pulses
        # can enter a blue refight pad before the intended test even starts.
        r.fixture(3, 14)
        s.wait(prefix + '-hub-arrival', lambda row:
               row['stage'] == 12 and row['section'] == 0 and row['checkpoint'] == 14 and
               row['mode'][:2] == [6, 0] and not row['blocked'] and
               row['players'][leader]['state'] == 1 and
               row['players'][leader]['action'] == 2 and
               row['players'][leader]['grounded'] and
               1700 <= row['players'][leader]['x'] <= 1850 and
               1060 <= row['players'][leader]['y'] <= 1100 and
               all(row['players'][seat]['active'] and
                   row['players'][seat]['visible'] and
                   row['players'][seat]['state'] == 1 and
                   row['players'][seat]['action'] == 2 and
                   not row['players'][seat]['script'] and
                   not row['players'][seat]['door'] for seat in live), 25)
        hub = s.sample(prefix + '-hub', True)
        assert (hub['stage'], hub['section'], hub['checkpoint']) == (12, 0, 14), hub
        lives = hub['lives']
        # Locate the actual native pad whose authored destination is10,
        # rather than guessing a platform from a neighboring refight room.
        end = time.monotonic() + 10
        yellow = None
        while time.monotonic() < end:
            pool = r.read(0x80165A30, 32 * 0x8C)
            pads = []
            for slot in range(32):
                actor = pool[slot * 0x8C:(slot + 1) * 0x8C]
                if actor[0] and actor[1] == 27:
                    pads.append(dict(slot=slot, variant=actor[2], state=list(actor[4:8]),
                                     x=struct.unpack_from('<i', actor, 8)[0] / 65536,
                                     y=struct.unpack_from('<i', actor, 12)[0] / 65536))
            yellow = next((pad for pad in pads if pad['variant'] & 15 == 10), None)
            if yellow:
                break
            time.sleep(.05)
        assert yellow, ('Native yellow pad was not admitted', pads)
        # Position just outside that pad's collision box; native movement
        # and falling/landing must perform the actual admission.
        if dead is None:
            # Commit both positions at the same boundary: moving only P1
            # first may start the pad before a second fixture is admitted.
            r.teleport_both(int(yellow['x']) - 40, int(yellow['y']) - 40)
        else:
            r.teleport(leader, int(yellow['x']) - 40, int(yellow['y']) - 40)
        for seat in live:
            r.input(0xFFDF, seat)
        try:
            arrival = s.wait(prefix + '-yellow-pad', lambda row:
                             row['stage'] == 12 and row['section'] == 0 and
                             row['checkpoint'] == 10 and row['mode'][0] == 6 and
                             row['players'][leader]['state'] == 1 and
                             row['players'][leader]['grounded'] and
                             1800 <= row['players'][leader]['x'] <= 2040 and
                             2500 <= row['players'][leader]['y'] <= 2510, 25)
        finally:
            r.release()
        if dead is not None:
            assert arrival['players'][dead]['hp'] == 0, arrival
        assert all(arrival['players'][seat]['hp'] for seat in live), arrival
        assert arrival['lives'] == lives and arrival['campaign'] == s.campaign, arrival
        s.sample(prefix + '-corridor', True)

        r.input(0xFFDF, leader)
        try:
            admitted = s.wait(prefix + '-scene-admission', lambda row:
                              row['stage'] == 12 and row['section'] == 0 and
                              row['checkpoint'] == 10 and row['blocked'] and
                              row['players'][leader]['script'], 15)
        finally:
            r.release()
        if dead is not None:
            assert admitted['players'][dead]['hp'] == 0, admitted
        assert all(admitted['players'][seat]['hp'] for seat in live), admitted
        assert admitted['lives'] == lives and admitted['campaign'] == s.campaign, admitted
        s.sample(prefix + '-scene', True)

        # The authored scene carries the entrant directly into section1.
        # Confirm dialogue with the owning seat, then release input before
        # checking idle controls; repeatedly pressing Jump is not an idle test.
        end = time.monotonic() + 120
        transition_seen = False
        while time.monotonic() < end:
            row = s.sample(prefix + '-dialogue')
            if row['stage'] == 12 and row['section'] == 1 and row['mode'][0] == 6:
                break
            if row['section'] == 0 and dead is not None:
                assert row['players'][dead]['hp'] == 0, row
            # Mode10 plays movie9 in Zero's campaign; X uses it only for the
            # transition. Its global input reads pad1, independently of the
            # in-stage owner. Exercise native Start rather than waiting for
            # full playback; this does not qualify a P2-only movie skip.
            transition_seen |= row['mode'][0] == 10
            r.input(0xFFF7 if row['mode'][0] == 10 else 0xBFFF,
                    0 if row['mode'][0] == 10 else leader)
            time.sleep(.12)
            r.release()
            time.sleep(.08)
        else:
            raise AssertionError(('Sigma scene did not complete its native transfer', row))
        r.release()
        # Zero has a second authored conversation after the FMV/section load.
        # New-section revival restores P1's campaign authority here. Let the
        # native sequel finish with confirm input before testing neutral idle.
        s.wait(prefix + '-section-dialogue', lambda row:
               row['stage'] == 12 and row['section'] == 1 and
               row['mode'][:2] == [6, 0] and not row['blocked'] and
               not row['warning'], 60, confirm=True)
        r.release()
        released = s.wait(prefix + '-section-ready', lambda row:
                          row['stage'] == 12 and row['section'] == 1 and
                          row['mode'][:2] == [6, 0] and not row['blocked'] and
                          all(p['active'] and p['visible'] and p['hp'] and
                              p['state'] == 1 and p['action'] == 2 and
                              not p['script'] and not p['door'] for p in row['players']), 20)
        assert released['lives'] == lives and released['campaign'] == s.campaign, released
        s.sample(prefix + '-section-ready', True)
        # The existing forward-area policy legitimately revives a dead partner
        # after the scene. Do not mistake that revival for an admission bypass.
        before = [p['x'] for p in released['players']]
        for seat in (0, 1):
            r.input(0xFFDF, seat)
        try:
            moved = s.wait(prefix + '-section-movement', lambda row:
                           all(row['players'][seat]['x'] > before[seat] + 8
                               for seat in (0, 1)), 5)
        finally:
            r.release()
        cases.append(dict(name=name, prior_refights='bypassed prerequisites',
                          native_pad=yellow, yellow_pad=arrival, scene=admitted, forward_section=released,
                          transition_mode_seen=transition_seen,
                          global_transition_control='native pad1 Start' if transition_seen else 'not entered',
                          movement=moved, lives_preserved=True))
    return dict(campaign=s.campaign, cases=cases, method=__doc__)
