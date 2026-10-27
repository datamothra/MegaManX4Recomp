"""Native Both-door animation and progression, using the Jungle checkpoint.

Fixtures select a checkpoint and prepare approach positions.
Controller input must admit, open and close the actual door, start the boss
introduction, and regain control. No door/animation/progression flags are set.
"""
import json
import struct
import time

from coop_debug import capture_pair


def door_animation(s, *, require_advance=True):
    r = s.r
    results = []
    diagnostic = r.diagnostic()
    addresses = [diagnostic + 0x300, diagnostic + 0x100, 0x801721c0]
    for slot, address in enumerate(addresses):
        r.request('set_snapshot', slot=slot, addr=hex(address))

    def counters():
        return {v['name']: v['count'] for v in r.request('mod_counters')['counters']}

    def doors():
        pool = r.read(0x80165a30, 32 * 0x8c)
        return [(0x80165a30 + i, pool[i:i + 0x8c])
                for i in range(0, len(pool), 0x8c)
                if pool[i] and pool[i + 1] == 8]

    def history(start, end, actor):
        rows = []
        for frame in range(start, end + 1):
            try:
                values = [bytes.fromhex(r.request('read_frame_ram', frame=frame,
                          addr=hex(a), len=128)['hex']) for a in addresses]
                door = bytes.fromhex(r.request('read_frame_ram', frame=frame,
                                     addr=hex(actor), len=128)['hex'])
            except RuntimeError:
                continue
            rows.append(dict(frame=frame, bodyhex=[b.hex() for b in values[:2]],
                             playhex=values[2].hex(), doorhex=door.hex()))
        return rows

    for kind in ('walk', 'dash'):
        s.load(1, 1, 5)
        r.fixture(5, 0)  # Keep actual damage/death admission active.
        s.wait(kind + '-grounded', lambda v: all(p['grounded'] for p in v['players']), 15)
        before = s.sample(kind + '-before')
        available = doors()
        x = max(p['x'] for p in before['players'])
        actor, body = min((v for v in available if struct.unpack_from('<h', v[1], 10)[0] > x),
                          key=lambda v: struct.unpack_from('<h', v[1], 10)[0])
        door_x = struct.unpack_from('<h', body, 10)[0]
        # Same safe checkpoint floor, within one dash of the real aperture.
        r.teleport_both(door_x - 64, int(before['players'][0]['y']))
        s.wait(kind + '-approach-grounded', lambda v: all(p['grounded'] for p in v['players']), 10)
        r.request('set_snapshot', slot=3, addr=hex(actor))
        initial = counters()
        start = r.request('mod_counters')['frame']
        observations = []
        opened = False
        closed = False
        opening_shots = []
        prefix = 'door-animation-' + kind
        try:
            for seat in (0, 1):
                r.input(0xffdf if kind == 'walk' else 0xdfdf, seat)
            deadline = time.monotonic() + 25
            while time.monotonic() < deadline:
                v = s.sample(prefix)
                door = r.read(actor, 128)
                observations.append(dict(frame=v['frame'], door=list(door[:7]), state=v))
                assert all(p['hp'] and p['state'] == 1 for p in v['players']), v
                if (door[4:6] == bytes((1, 2)) and len(opening_shots) < 3 and
                        (not opening_shots or v['frame'] >= opening_shots[-1] + 15)):
                    capture_pair(r, s.output/(prefix + '-opening-' + str(len(opening_shots)) + '.png'))
                    opening_shots.append(v['frame'])
                opened |= door[4] == 1 and door[5] == 3
                crossed = counters().get('mmx4.coop.both-door-crossings', 0) > initial.get('mmx4.coop.both-door-crossings', 0)
                closed |= crossed and (door[5] == 4 or door[4] >= 2)
                if opened and closed:
                    break
                time.sleep(.01)
            else:
                raise AssertionError(('Actual Both-door did not open and close', kind, observations[-1]))
            r.release()
            r.request('capture_mark', op='mark')
            end = r.request('mod_counters')['frame']
            try:
                rows = history(start, end, actor)
            finally:
                r.request('capture_mark', op='release')
            (s.output/(prefix + '-frames.json')).write_text(json.dumps(rows, indent=2) + '\n')
            capture_pair(r, s.output/(prefix + '-closed.png'))
            locked = [v for v in rows if bytes.fromhex(v['playhex'])[0x10] and
                      bytes.fromhex(v['doorhex'])[4:6] == bytes((1, 2))]
            assert len(locked) >= 6, ('Opening lock not captured', kind, len(locked))
            admission = next(v for v in rows if bytes.fromhex(v['doorhex'])[5] == 1)
            animation = []
            for seat in (0, 1):
                # The door asserts PLAY+10 after this update's body passes.
                # The following update is the first suspended body pass;
                # normalizing at assertion time would advance it twice.
                eligible = locked[1:]
                bodies = [bytes.fromhex(v['bodyhex'][seat]) for v in eligible]
                sprites = sorted({b[0x47] for b in bodies})
                timers = sorted({b[0x44] for b in bodies})
                incoming = bytes.fromhex(admission['bodyhex'][seat])[0x17]
                if require_advance:
                    allowed = (8, 0x26) if kind == 'walk' else (16,)
                    assert all(b[0x17] in allowed for b in bodies), ('Incorrect native door clip', kind, seat)
                    if incoming in (8, 16):
                        assert all(b[0x17] == incoming for b in bodies), ('Incoming clip was replaced', kind, seat)
                    assert len({b[8:16] for b in bodies}) == 1, ('Opening animation moved a body', kind, seat)
                checks = 0
                for prev, cur, a, b in zip(eligible, eligible[1:], bodies, bodies[1:]):
                    if cur['frame'] == prev['frame'] + 1:
                        if require_advance:
                            cursor = struct.unpack_from('<I', a, 0x34)[0]
                            expected = cursor
                            if a[0x44] == 1:
                                expected = (cursor + struct.unpack_from('<b', a, 0x46)[0] * 4) & 0xffffffff
                            else:
                                assert b[0x44] == (a[0x44] - 1) & 255, ('Animation timer did not advance once', kind, seat, prev, cur)
                            assert struct.unpack_from('<I', b, 0x34)[0] == expected, ('Animation cursor did not advance once', kind, seat, prev, cur)
                        checks += 1
                if require_advance:
                    assert len(sprites) >= 2 and checks >= 3, ('Frozen door animation', kind, seat, sprites, checks)
                animation.append(dict(seat=seat, native_sprites=sprites, timers=timers,
                                      incoming_program=incoming, selected_program=bodies[0][0x17],
                                      consecutive_animation_checks=checks))
            # Continue into the actual boss scene, confirming text via input.
            s.watch_enemy = 43
            deadline = time.monotonic() + 65
            introduction = False
            while time.monotonic() < deadline:
                v = s.sample(prefix + '-introduction')
                bosses = [e for e in s.enemies() if e['type'] == 43]
                introduction |= bool(bosses) and bool(v['blocked'] or any(p['script'] for p in v['players']))
                if (introduction and bosses and bosses[0]['hp'] == 48 and not v['blocked'] and
                        all(not p['script'] and not p['door'] and p['state'] == 1 for p in v['players'])):
                    break
                for seat in (0, 1):
                    r.input(0xbfff if v['blocked'] else 0xffdf, seat)
                time.sleep(.06)
                if v['blocked']:
                    r.release()
                    time.sleep(.06)
            else:
                raise AssertionError(('Native boss introduction did not release controls', kind, v, s.enemies()))
            r.release()
            controls = []
            for seat in (0, 1):
                grounded = s.wait(prefix + '-ground', lambda v: all(p['grounded'] for p in v['players']), 8)
                r.input(0xbfff, seat)
                jumped = s.wait(prefix + '-jump', lambda v: v['players'][seat]['y'] < grounded['players'][seat]['y'] - 20, 3)
                r.release()
                controls.append(dict(seat=seat, y_delta=jumped['players'][seat]['y'] - grounded['players'][seat]['y']))
            assert v['lives'] == before['lives'] and all(p['hp'] for p in v['players'])
            capture_pair(r, s.output/(prefix + '-controls.png'))
            result = dict(kind=kind, opening_frames=len(locked), animation=animation,
                          native_opening=True, native_closing=True,
                          actual_boss_introduction=True, controls=controls)
            results.append(result)
            print(json.dumps(result), flush=True)
        finally:
            r.release()
            (s.output/(prefix + '-events.json')).write_text(json.dumps(observations, indent=2) + '\n')
            (s.output/'door-animation-results.json').write_text(json.dumps(results, indent=2) + '\n')
    render = r.request('render_pass_stats')
    if require_advance:
        assert render['verify_checks'] > 0 and all(render[k] == 0 for k in
               ('verify_mismatch', 'vram_leaks', 'aborted', 'watchdog')), render
    return dict(doors=results, render=render)
