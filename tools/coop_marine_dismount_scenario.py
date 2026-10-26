"""Native Chaser ejection, landing, movement and subsequent boss admission.

Fixtures position riders/camera on the final platform before autoscroll ends.
They never set the dismount flag, rider action, floor contact or checkpoint.
"""
import json
import struct
import time
from coop_debug import capture_pair


def marine_dismount(s):
    r = s.r
    r.fixture(5, 3)
    s.load(5, 1, 1)
    floor = s.wait('marine-original-foot-checkpoint',
                   lambda v: all(p['grounded'] for p in v['players']), 15)
    s.load(0, 0); s.load(5, 1)
    diagnostic = r.diagnostic()

    def ready(_):
        data = r.read(diagnostic, 0x6d0)
        return all(data[a] and data[a+4:a+6] == bytes([1, 1])
                   for a in (0x620, 0x200))

    s.wait('marine-bikes-ready', ready, 25)
    r.input(0xfff7, 0); time.sleep(.15); r.release()
    s.wait('marine-setup-paused', lambda v: v['mode'][:2] == [6, 2] and
           v['menu'][0] == 1 and v['menu'][1] < 3, 10)
    time.sleep(.3)
    r.teleport_both(16460, int(floor['players'][0]['y']) - 80)
    r.teleport(1, 16436, int(floor['players'][0]['y']) - 80)
    # The Chaser consumes current-minus-previous camera X. Its current left
    # clip also advances toward authored target16384. Prepare those positions
    # together while paused, leaving the target and native exit flag intact.
    split = next((c['count'] for c in r.request('mod_counters')['counters']
                  if c['name'] == 'mmx4.coop.split-state'), 0)
    cameras = [0x801419b0]
    if split:
        cameras.extend(split + 16 + seat * 0xfc for seat in (0, 1))
    for camera in cameras:
        for offset in (8, 0x14):
            for byte in range(4):
                r.write(camera + offset + byte, ((16300 << 16) >> (8*byte)) & 255)
        for byte in range(2):
            r.write(camera + 0x1e + byte, (16300 >> (8*byte)) & 255)
    assert not r.read(0x80141a01, 1)[0], 'Setup skipped the native exit trigger'
    s.sample('marine-before-native-exit', True)
    r.release(); time.sleep(.5)
    r.input(0xfff7, 0); time.sleep(.15); r.release()
    s.wait('marine-setup-resumed', lambda v: v['mode'][:2] == [6, 0], 10)
    rows = []
    try:
        for seat in (0, 1):
            r.input(0xffdf, seat)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            data = r.read(diagnostic, 0x6d0)
            players = []
            for at in (0x300, 0x100):
                p = data[at:at+0xe4]
                players.append(dict(state=p[4], action=p[5], substate=p[6],
                    hp=p[0x5c] & 127, mounted=p[0xc5], script=p[0xc0],
                    x=struct.unpack_from('<i', p, 8)[0]/65536,
                    y=struct.unpack_from('<i', p, 12)[0]/65536,
                    grounded=bool(p[0x89] & 8)))
            rows.append(dict(frame=struct.unpack_from('<I', data, 4)[0], players=players))
            assert all(p['hp'] == 32 and p['state'] == 1 for p in players), rows[-1]
            if all(not p['mounted'] and p['grounded'] and
                   p['action'] in (2, 4) for p in players):
                break
            time.sleep(.025)
        else:
            raise TimeoutError('Both riders did not complete native ejection and landing')
    finally:
        r.release()
        (s.output/'marine-ejection-frames.json').write_text(json.dumps(rows, indent=2)+'\n')
    assert all(any(row['players'][seat]['action'] == 0x17 for row in rows)
               for seat in (0, 1)), 'Each rider must execute the original ejection pose'
    assert r.read(0x80141a01, 1)[0], 'Native autoscroll did not issue the exit'
    landed = s.wait('marine-both-landed', lambda v: not v['blocked'] and all(
        p['hp'] == 32 and p['state'] == 1 and p['action'] == 2 and
        p['grounded'] and not p['script'] for p in v['players']), 15)
    s.sample('marine-both-landed', True)
    capture_pair(r, s.output/'marine-both-landed-presentation.png')
    assert landed['lives'] == floor['lives'], 'Dismount consumed a shared life'
    for seat in (0, 1):
        r.input(0xffdf, seat)
    try:
        # Wait for real controller movement, rather than assuming a fixed
        # wall-clock delay contains enough native simulation ticks.
        controlled = s.wait('marine-controls-restored', lambda v: all(
            a['x'] > b['x'] + 20 and a['hp'] == 32
            for a, b in zip(v['players'], landed['players'])), 10)
    finally:
        r.release()
    s.sample('marine-controls-restored', True)
    approach = []
    try:
        # The native WARNING controller must run its complete timed sequence.
        # Instrumented builds can advance fewer than 300 native frames in 40s.
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            row = s.sample('marine-original-boss-admission')
            bosses = [e for e in s.enemies() if e['type'] == 56]
            approach.append(dict(frame=row['frame'], players=row['players'],
                                 bounds=row['bounds'], bosses=bosses))
            if (all(p['x'] >= 17024 and p['hp'] == 32 and p['state'] == 1
                    for p in row['players']) and row['bounds'][1] >= 17024 and any(
                    e['hp'] > 1 and e['state'][0] == 1 for e in bosses)):
                break
            # Generic wait(confirm=True) releases every button after each
            # dialogue edge. Reapply movement through the introduction and
            # passenger return; allocation of the boss alone is insufficient.
            buttons = 0xbfdf if row['blocked'] and int(time.monotonic()*8) % 2 else 0xffdf
            for seat in (0, 1):
                r.input(buttons, seat)
            time.sleep(.03)
        else:
            raise TimeoutError(('Both riders did not enter the actual boss arena', row))
    finally:
        r.release()
        (s.output/'marine-arena-approach.json').write_text(json.dumps(approach, indent=2)+'\n')
    arena = s.wait('marine-boss-controls', lambda v: not v['blocked'] and
        not v['warning'] and not v['freeze'] and all(p['hp'] == 32 and
            p['state'] == 1 and p['action'] == 2 and p['grounded'] and
            p['x'] >= 17024 and not p['door'] and not p['script']
            for p in v['players']), 25, confirm=True)
    s.sample('marine-boss-controls', True)
    capture_pair(r, s.output/'marine-boss-presentation.png')
    assert arena['lives'] == floor['lives']
    boss_positions = []
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        boss = next((e for e in s.enemies() if e['type'] == 56 and
                     e['state'][0] == 1 and e['hp'] > 1), None)
        assert boss is not None, 'Jet disappeared after the physical door handoff'
        boss_positions.append((boss['x'], boss['y']))
        time.sleep(.08)
    assert len(set(boss_positions)) > 1, 'The admitted boss never moved'
    capture_pair(r, s.output/'marine-boss-active-presentation.png')
    counters = r.request('mod_counters')['counters']
    return dict(landed=landed, controlled=controlled, boss_admission=arena,
                ejection_observations=len(rows), live_boss_positions=boss_positions,
                prefetch_waits=[c for c in counters if 'jet-prefetch-waits' in c['name']])
