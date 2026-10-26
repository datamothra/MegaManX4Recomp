"""Let either rider finish Marine's bike route without moving the other view.

Only player/vehicle and camera positions are prepared. Native autoscroll,
exit controllers, rider poses, collision and landing must perform the exit.
"""
import json
import struct
import time
from coop_debug import capture_pair


def chaser_independence(s):
    r = s.r
    r.fixture(5, 3)
    s.load(5, 1, 1)
    floor = s.wait('independent-exit-native-floor',
                   lambda v: all(p['grounded'] for p in v['players']), 15)
    results = []

    def pause():
        r.input(0xfff7, 0); time.sleep(.15); r.release()
        s.wait('independent-exit-setup-paused', lambda v: v['mode'][:2] == [6, 2]
               and v['menu'][0] == 1 and v['menu'][1] < 3, 12)
        time.sleep(.3)

    def resume():
        r.input(0xfff7, 0); time.sleep(.15); r.release()
        s.wait('independent-exit-setup-resumed', lambda v: v['mode'][:2] == [6, 0], 12)

    def put(at, value, size):
        for byte in range(size):
            r.write(at + byte, (value >> (8 * byte)) & 255)

    def prepare_exit(seat, split):
        r.teleport(seat, 16460, int(floor['players'][seat]['y']) - 80)
        cameras = [split + 16 + seat * 0xfc]
        if not seat:
            cameras.append(0x801419b0)
        for camera in cameras:
            for offset in (8, 20):
                put(camera + offset, 16300 << 16, 4)
            put(camera + 0x1e, 16300, 2)
        assert not r.read(cameras[0] + 0x51, 1)[0], 'Fixture skipped native exit'

    for leader in (0, 1):
        # Clear the preceding section's authored controller before reloading.
        s.load(0, 0); s.load(5, 1)
        diagnostic = r.diagnostic()
        split = next(c['count'] for c in r.request('mod_counters')['counters']
                     if c['name'] == 'mmx4.coop.split-state')

        def read():
            m = r.read(diagnostic, 0x6d0)
            cameras = r.read(split, 16 + 2 * 0xfc)
            return dict(tick=struct.unpack_from('<I', m, 4)[0], players=[
                dict(state=m[a+4], action=m[a+5], hp=m[a+0x5c] & 127,
                     mounted=m[a+0xc5], x=struct.unpack_from('<i', m, a+8)[0]/65536,
                     y=struct.unpack_from('<i', m, a+12)[0]/65536,
                     grounded=bool(m[a+0x89] & 8)) for a in (0x300, 0x100)],
                vehicles=[list(m[a+4:a+7]) for a in (0x620, 0x200)],
                exits=[cameras[16+seat*0xfc+0x51] for seat in (0, 1)],
                camera_x=[struct.unpack_from('<i', cameras, 16+seat*0xfc+8)[0]/65536
                          for seat in (0, 1)])

        s.wait('independent-exit-both-bikes', lambda _: all(
            v[:2] == [1, 1] for v in read()['vehicles']), 30)
        pause(); prepare_exit(leader, split)
        capture_pair(r, s.output / f'independent-exit-{leader}-before.png')
        resume()
        rows = []
        try:
            for exiting in (leader, leader ^ 1):
                if exiting != leader:
                    pause()
                    # Current-build state must retain one finished controller
                    # and one pending controller, then finish the native exit.
                    for op in ('save', 'load'):
                        generation = r.request('savestate_status')['generation']
                        r.request('savestate', op=op, slot=1)
                        deadline = time.monotonic() + 25
                        while time.monotonic() < deadline:
                            status = r.request('savestate_status')
                            if status['generation'] != generation and not status['pending']:
                                assert status['last_ok'] and status['last_op'] == op, status
                                break
                            time.sleep(.03)
                        else:
                            raise TimeoutError('Independent exit snapshot ' + op)
                    saved = read()
                    assert saved['exits'][leader] == 1 and saved['exits'][exiting] == 0, saved
                    prepare_exit(exiting, split); resume()
                r.input(0xffdf, exiting)
                deadline = time.monotonic() + 25
                while time.monotonic() < deadline:
                    row = read(); rows.append(row)
                    assert all(p['hp'] == 32 and p['state'] == 1 for p in row['players']), row
                    if exiting == leader:
                        other = exiting ^ 1
                        assert row['players'][other]['mounted'] == 255 and row['vehicles'][other][0] == 1, (
                            'Leading rider ended the trailing ride', row)
                        assert row['exits'][other] == 0, ('Shared end-of-ride flag', row)
                    p = row['players'][exiting]
                    if not p['mounted'] and p['grounded'] and p['action'] in (2, 4):
                        if exiting == leader:
                            assert abs(row['camera_x'][0] - row['camera_x'][1]) > 10000, (
                                'Leading exit moved the trailing camera', row)
                        break
                    time.sleep(.025)
                else:
                    raise TimeoutError(('Native independent exit did not land', exiting, rows[-1]))
                r.release()
                capture_pair(r, s.output / f'independent-exit-{leader}-seat{exiting}-landed.png')
            landed = s.wait('independent-exit-both-landed', lambda v: not v['blocked'] and all(
                p['grounded'] and p['hp'] == 32 and not p['script'] for p in v['players']), 15)
            assert landed['lives'] == floor['lives'], 'Independent exit consumed a shared life'
            assert all(any(row['players'][seat]['action'] == 0x17 for row in rows)
                       for seat in (0, 1)), 'Missing native rider ejection pose'
            results.append(dict(leader=leader, both_native_landings=True,
                                trailing_ride_preserved=True, snapshot_restored=True,
                                observations=len(rows), final=read()))
        finally:
            r.release()
            (s.output / f'independent-exit-{leader}-frames.json').write_text(json.dumps(rows, indent=2) + '\n')
    return dict(independent_exits=results)
