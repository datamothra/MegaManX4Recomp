"""Jet's paired boss door, including a partner waiting on the upper ledge.

Position/protection fixtures prepare the on-foot checkpoint. Native movement,
room bounds, falling, boss introduction and restored controls prove admission.
"""
import json
import time

from coop_debug import capture_pair


def jet_door(s, arrangements=((0, False), (1, False), (0, True), (1, True))):
    r = s.r
    cases = []
    s.watch_enemy = 56
    for leader, wait_outside in arrangements:
        prefix = f'jet-door-p{leader+1}-wait{int(wait_outside)}'
        r.fixture(5, 3)
        s.load(5, 1, 1)
        r.fixture(5, 3)
        initial = s.wait(prefix+'-checkpoint', lambda v: all(
            p['grounded'] and p['action'] == 2 for p in v['players']), 15)
        y = int(initial['players'][0]['y'])
        r.teleport_both(16848, y)
        r.teleport(leader, 16936, y)
        time.sleep(1)
        rows = []
        both_admitted = False
        released_partner = not wait_outside
        landed_at = None
        deadline = time.monotonic() + 100
        try:
            while time.monotonic() < deadline:
                v = s.sample(prefix+'-approach')
                rows.append(v)
                assert all(p['hp'] and p['state'] == 1 for p in v['players']), (
                    'Hero died crossing the original door', v)
                both_admitted |= all(p['door'] == 255 for p in v['players'])
                if (both_admitted and not released_partner and
                        v['players'][leader]['grounded'] and
                        v['players'][leader]['y'] > 280):
                    if landed_at is None:
                        landed_at = time.monotonic()
                        assert v['players'][leader ^ 1]['x'] < 17024, v
                        capture_pair(r, s.output/(prefix+'-waiting.png'))
                    if time.monotonic()-landed_at > 1:
                        released_partner = True
                bosses = [e for e in s.enemies() if e['type'] == 56]
                if (released_partner and bosses and bosses[0]['hp'] == 48 and
                        bosses[0]['state'][0] == 1 and not v['blocked'] and
                        not v['warning'] and all(p['action'] == 2 and p['grounded'] and
                            not p['door'] and not p['script'] for p in v['players'])):
                    break
                for seat in (0, 1):
                    if v['blocked']:
                        buttons = 0xbfdf if int(time.monotonic()*8) % 2 else 0xffdf
                    elif both_admitted and seat != leader and not released_partner:
                        buttons = 0xffff
                    elif both_admitted and seat == leader and v['players'][seat]['x'] > 17150:
                        buttons = 0xffff
                    else:
                        buttons = 0xffdf
                    r.input(buttons, seat)
                time.sleep(.03)
            else:
                capture_pair(r, s.output/(prefix+'-failed.png'))
                raise AssertionError(('Native Jet admission did not return both controls', v))
        finally:
            r.release()
            (s.output/(prefix+'-frames.json')).write_text(json.dumps(rows, indent=2)+'\n')
        assert both_admitted and (not wait_outside or landed_at is not None)
        capture_pair(r, s.output/(prefix+'-fight.png'))
        movements = []
        for seat in (0, 1):
            before = s.sample(prefix+'-control-before')
            r.input(0xff7f, seat)
            deadline = time.monotonic()+3
            try:
                while time.monotonic()<deadline:
                    time.sleep(.05)
                    after = s.sample(prefix+'-control-after')
                    dx = after['players'][seat]['x']-before['players'][seat]['x']
                    if dx < -5:
                        break
                else:
                    raise AssertionError(('Native control missing after door', seat, before, after))
            finally:
                r.release()
            movements.append(dx)
        assert v['lives'] == initial['lives'], 'Door crossing consumed a shared life'
        cases.append(dict(leader=leader, wait_outside=wait_outside, players=v['players'],
                          minimum_hp=[min(v['players'][seat]['hp'] for v in rows)
                                      for seat in (0, 1)], controls=movements))
    return dict(native_paired_admissions=cases)
