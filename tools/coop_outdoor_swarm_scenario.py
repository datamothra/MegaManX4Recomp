"""Sky Lagoon part1's native opening swarm, with either hero leading."""
import json
import time

from coop_debug import capture_pair
from coop_fortress_followup_scenario import actors


def outdoor_swarm(s):
    r = s.r
    results = []
    for leader in (0, 1):
        s.load(0, 0, 0)
        r.fixture(5, 3)
        initial = actors(s)
        swarm = {a['address'] for a in initial if a['pool'] == 'enemy' and
                 a['type'] == 10 and 3 <= a['flags'][2] <= 8}
        assert len(swarm) == 10, ('Opening swarm did not allocate', initial)
        before = s.sample('outdoor-swarm-start-' + str(leader))
        rows = []
        captured = False

        def observe(label):
            nonlocal captured
            row = s.sample(label)
            row['actors'] = actors(s)
            rows.append(row)
            if not captured and any(a['address'] in swarm and a['flags'][3]
                                    for a in row['actors']):
                capture_pair(r, s.output / ('outdoor-swarm-' + str(leader) + '-visible.png'))
                captured = True
            return row

        try:
            r.input(0xffdf, leader)
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                row = observe('outdoor-swarm-approach-' + str(leader))
                if row['players'][leader]['x'] >= 400:
                    break
                time.sleep(.04)
            else:
                raise AssertionError(('Leader did not reach native swarm trigger', row))
        finally:
            r.release()
        # Observe actual motion/drawing after native activation. Do not set
        # enemy state, coordinates, timers or the predicate being qualified.
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            row = observe('outdoor-swarm-visible-' + str(leader))
            time.sleep(.04)
        (s.output / ('outdoor-swarm-' + str(leader) + '.json')).write_text(
            json.dumps(dict(initial=initial, before=before, rows=rows), indent=2) + '\n')
        capture_pair(r, s.output / ('outdoor-swarm-' + str(leader) + '.png'))
        activated = {a['address'] for row in rows for a in row['actors']
                     if a['address'] in swarm and a['flags'][5] == 6}
        drawable = {a['address'] for row in rows for a in row['actors']
                    if a['address'] in swarm and a['flags'][3]}
        assert activated == swarm, ('Waiting partner blocked the opening swarm', leader, activated, swarm)
        assert drawable, ('Activated swarm was never drawable', leader)
        assert abs(rows[-1]['players'][leader ^ 1]['x'] -
                   before['players'][leader ^ 1]['x']) < 1, 'Partner did not remain behind'
        results.append(dict(leader=leader, activated=sorted(activated), drawable=sorted(drawable)))
    return dict(native_outdoor_opening_swarm=results)
