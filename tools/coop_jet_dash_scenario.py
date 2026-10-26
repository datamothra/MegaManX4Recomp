"""Native Ride Chaser dashes must preserve the other rider's scroll speed.

Native loads and damage protection prepare each case. The original vehicle
controller, dash and camera updates supply all observed movement.
"""
import json
import struct
import time


def jet_dash(s):
    r = s.r
    cases = []
    for section in (0, 1):
        for dasher in (0, 1):
            r.fixture(5, 3)
            if not section:
                s.jet_intro()
            else:
                s.load(5, 1)
            diagnostic = r.diagnostic()

            def read():
                m = r.read(diagnostic, 0x6d0)
                assert struct.unpack_from('<I', m, 0x1c)[0] == 1
                return dict(tick=struct.unpack_from('<I', m, 4)[0],
                    bikes=[dict(state=list(m[a+4:a+7]),
                                x=struct.unpack_from('<i', m, a+8)[0]/65536,
                                hp=m[a+0x5c] & 127)
                           for a in (0x620, 0x200)])

            deadline = time.monotonic() + 25
            while time.monotonic() < deadline:
                v = read()
                if all(b['state'][:2] == [1, 1] for b in v['bikes']):
                    break
                time.sleep(.03)
            else:
                raise AssertionError(('Both bikes did not become controllable', v))
            r.release()
            rows = []
            started = time.monotonic()
            try:
                while time.monotonic() - started < 2.5:
                    elapsed = time.monotonic() - started
                    r.input(0xdfff if .35 < elapsed < 1.5 else 0xffff, dasher)
                    v = read()
                    v['elapsed'] = elapsed
                    rows.append(v)
                    time.sleep(.03)
            finally:
                r.release()
                (s.output / f'jet-dash-section{section}-seat{dasher}.json').write_text(
                    json.dumps(rows, indent=2) + '\n')
            assert any(v['bikes'][dasher]['state'][1] == 5 for v in rows), 'No native dash'
            speeds = [[], []]
            for before, after in zip(rows, rows[1:]):
                ticks = after['tick'] - before['tick']
                if ticks <= 0:
                    continue
                assert all(b['hp'] for b in after['bikes']), ('Rider died', after)
                for seat in (0, 1):
                    speeds[seat].append((after['bikes'][seat]['x'] -
                                         before['bikes'][seat]['x']) / ticks)
            assert speeds[dasher] and max(speeds[dasher]) > 7, ('Dash did not accelerate rider', speeds)
            assert speeds[dasher ^ 1] and all(abs(v - 6) < .01 for v in speeds[dasher ^ 1]), (
                'Partner accelerated without input', section, dasher, speeds)
            s.sample(f'jet-dash-section{section}-seat{dasher}', True)
            cases.append(dict(section=section, dasher=dasher, maximum_speed=[max(v) for v in speeds],
                              neutral_speed=6, observations=len(rows)))
    return dict(independent_bike_dashes=cases)
