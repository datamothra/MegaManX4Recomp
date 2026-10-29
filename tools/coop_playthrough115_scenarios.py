"""Bounded reproductions from the owner's complete stable1.0.15 playthrough."""
import json
import struct
import time

from coop_debug import capture_pair


def _native_dialogue_wait(s, label, predicate, timeout=65):
    """Pulse the scene owner with a complete native controller-poll release."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        row = s.sample(label)
        if predicate(row):
            return row
        if row['blocked']:
            living = [(i, p) for i, p in enumerate(row['players'])
                      if p['active'] and p['visible'] and p['hp']]
            # A paired door can leave both bodies visible during text. The
            # native script marker identifies whose confirm input is routed.
            owner = next((i for i, p in living if p['script']),
                         living[0][0] if living else None)
            if owner is not None:
                s.r.input(0xdfff, owner)
                time.sleep(.15)
                s.r.release()
                time.sleep(.15)
        time.sleep(.04)
    raise TimeoutError((label, row))


def spider_door_scenery(s):
    r = s.r
    s.load(1, 1, 5)
    r.fixture(5, 0)
    s.wait('spider-floor', lambda v: all(p['grounded'] for p in v['players']))
    before = s.sample('spider-before-door')
    x = max(p['x'] for p in before['players'])
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        pool = r.read(0x80165a30, 32 * 0x8c)
        doors = [(0x80165a30 + i, struct.unpack_from('<h', pool, i + 10)[0])
                 for i in range(0, len(pool), 0x8c) if pool[i] and pool[i + 1] == 8
                 and struct.unpack_from('<h', pool, i + 10)[0] > x]
        if doors:
            break
        time.sleep(.05)
    assert doors, 'Native Spider door placement did not appear'
    actor, door_x = min(doors, key=lambda v: v[1])
    r.teleport_both(door_x - 64, 1467)
    state = next(c['count'] for c in r.request('mod_counters')['counters']
                 if c['name'] == 'mmx4.coop.split-state')
    rows = []
    try:
        for seat in (0, 1):
            r.input(0xffdf, seat)
        deadline = time.monotonic() + 30
        admitted = closed = False
        while time.monotonic() < deadline:
            v = s.sample('spider-door-scenery')
            body = r.read(actor, 0x8c)
            v['door_actor'] = body.hex()
            v['views'] = [list(struct.unpack('<126h', r.read(state + 16 + seat * 0xfc, 0xfc)))
                          for seat in (0, 1)]
            rows.append(v)
            assert all(p['hp'] for p in v['players']), v
            if body[5] and not admitted:
                admitted = True
                r.release()
            if admitted and (body[5] >= 4 or body[4] >= 2):
                closed = True
                break
            if len(rows) % 12 == 0:
                capture_pair(r, s.output / ('spider-door-' + str(len(rows)) + '.png'))
            time.sleep(.02)
        assert closed, ('Spider door did not close', rows[-1])
        mismatches = []
        crossing = [v for v in rows if bytes.fromhex(v['door_actor'])[4:6] == bytes((1, 3))]
        for v in crossing:
            for seat, camera in enumerate(v['views']):
                foreground_x = camera[10 // 2]
                background_x = camera[(0x54 + 10) // 2]
                offset = camera[(0x54 + 0x40) // 2]
                # Original D9138's mode5 boss-region parallax, evaluated from
                # this seat's completed foreground camera. No scene flags or
                # camera values are supplied by this check.
                delta = (foreground_x - 2400) >> 1
                expected = delta + (delta >> 1) + offset
                # TCP reads can straddle one native camera update (up to8px
                # of authored door easing); a stopped layer drifts >200px.
                if abs(background_x - expected) > 10:
                    mismatches.append(dict(frame=v['frame'], seat=seat, actual=background_x,
                                           expected=expected, foreground_x=foreground_x))
        capture_pair(r, s.output / 'spider-door-closed.png')
        s.watch_enemy = 43
        for seat in (0, 1):
            r.input(0xffdf, seat)
        s.wait('spider-introduction', lambda v: v['blocked'] or v['warning'], 20)
        r.release()
        ready = _native_dialogue_wait(s, 'spider-fight', lambda v: not v['blocked'] and not v['warning'] and
                       any(e['type'] == 43 and e['hp'] >= 32 and e['state'][0] == 1 for e in s.enemies()) and
                       all(p['hp'] and p['grounded'] and p['action'] == 2 and not p['script'] and
                           not p['door'] for p in v['players']))
        capture_pair(r, s.output / 'spider-scenery-fight.png')
        assert crossing and not mismatches, ('Spider scenery stopped following its own view', mismatches)
        return dict(native_door_closed=True, crossing_samples=len(crossing), fight=ready)
    finally:
        r.release()
        (s.output / 'spider-door-scenery-series.json').write_text(json.dumps(rows, indent=2) + '\n')


def sigma_survivor_victory(s):
    from coop_fortress_followup_scenario import cameras
    r = s.r
    admission = s.sigma_phase3_survivor()
    if hasattr(s, 'sigma_final_ready'):
        s.sigma_final_ready(admission)
    r.fixture(5, 2)
    r.fixture(7, 1, 0, 1)
    rows = []
    try:
        deadline = time.monotonic() + 200
        while time.monotonic() < deadline:
            v = s.sample('sigma-final-combat')
            bosses = [e for e in s.enemies() if e['type'] == 74]
            v['enemies'] = bosses
            rows.append(v)
            # The first head's native death animation returns this same actor
            # to combat with the other health pool. Phase3 is the actual
            # final-victory scene, after both forms have taken defeating hits.
            if bosses and bosses[0]['state'][0] == 2 and bosses[0]['state'][1] >= 3:
                break
            assert v['players'][0]['hp'] == 0 and v['players'][1]['hp'], v
            if bosses and bosses[0]['state'][0] == 2:
                time.sleep(.1)
                continue
            if bosses and bosses[0]['hp'] > 1:
                # Both live forms have their own HP. Prepare the currently
                # selected form only; actual attacks must defeat each one.
                r.fixture(6, bosses[0]['slot'], 1)
            if bosses and not s.campaign and hasattr(s, 'sigma_final_attack'):
                s.sigma_final_attack(bosses[0])
                continue
            x, y = (bosses[0]['x'], bosses[0]['y']) if bosses else (0, 0)
            if not 1050 <= x <= 1420 or not 580 <= y <= 720:
                time.sleep(.15)
                continue
            if not s.campaign:
                # Use the native vulnerable rectangle, then retreat before
                # the earth head's suction can pull Zero into its lethal pit.
                # A new script lock means the actual defeating hit already
                # committed the scene, so no further teleport is admissible.
                boss = r.read(0x8013bed0 + bosses[0]['slot'] * 0x9c, 0x9c)
                box = struct.unpack_from('<I', boss, 0x54)[0]
                assert 0x80010000 <= box < 0x80200000
                dx, dy, _, _ = struct.unpack('<bbBB', r.read(box, 4))
                px = 1176 if x + dx < 1250 else 1320
                r.teleport(1, px, min(714, int(y + dy) + 20))
                r.input(0xff7f if x + dx < px else 0xffdf, 1)
                time.sleep(.035)
                r.input(0x7fff, 1)
                time.sleep(.17)
                r.release()
                if not r.read(0x801721dc, 1)[0]:
                    r.teleport(1, 1320, 714)
                time.sleep(.22)
                continue
            if s.campaign:
                # X uses a native charged shot. Charge safely on the authored
                # floor, then align with the current face before releasing it.
                r.teleport(1, 1320, 714)
                r.input(0x7fff, 1)
                time.sleep(.7)
                r.teleport(1, 1320, 714)
                time.sleep(.7)
                selected = [e for e in s.enemies() if e['type'] == 74]
                if not selected or selected[0]['state'][0] != 1:
                    r.release()
                    continue
                bosses = selected
                x, y = bosses[0]['x'], bosses[0]['y']
                if not 1050 <= x <= 1420 or not 580 <= y <= 720:
                    r.release()
                    continue
            # Stay on the authored arena: the garbage head's left edge is
            # lethal terrain and the gun body's right edge is solid. Prepare
            # a real attack beside the currently selected vulnerable head.
            boss = r.read(0x8013bed0 + bosses[0]['slot'] * 0x9c, 0x9c)
            hitbox = struct.unpack_from('<I', boss, 0x54)[0]
            assert 0x80010000 <= hitbox < 0x80200000
            dx, dy, width, height = struct.unpack('<bbBB', r.read(hitbox, 4))
            assert width and height
            # The gun form's vulnerable face is99px above its actor origin;
            # attacking the origin hits its armored gun instead of its face.
            # Position beside the actual native damage rectangle.
            px = 1160 if x < 1250 else 1340
            r.teleport(1, px, min(714, int(y) + dy + 20))
            direction = 0xff7f if x < px else 0xffdf
            r.input(direction & (0x7fff if s.campaign else 0xffff), 1)
            time.sleep(.02)
            r.release()
            if not s.campaign:
                r.input(0x7fff, 1)
                time.sleep(.22)
                r.release()
            time.sleep(.32)
        else:
            raise AssertionError(('Final Sigma did not receive native defeating attacks', rows[-1]))
        capture_pair(r, s.output / 'sigma-final-defeated.png')
        deadline = time.monotonic() + 85
        while time.monotonic() < deadline:
            v = s.sample('sigma-final-conclusion')
            v['enemies'] = s.enemies()
            v['views'] = cameras(s)
            rows.append(v)
            if not any(e['type'] == 74 for e in v['enemies']) and not v['blocked']:
                break
            if v['blocked']:
                r.input(0xdfff, 1)
                time.sleep(.15)
                r.release()
                time.sleep(.15)
            time.sleep(.05)
        else:
            raise AssertionError(('Sigma native conclusion did not finish', rows[-1]))
        capture_pair(r, s.output / 'sigma-survivor-after-dialogue.png')
        assert v['views'][1][0x24 // 2:0x28 // 2] == [1152, 1104], ('Sigma ending camera remained enclosed', v)
        deadline = time.monotonic() + 65
        ending_dialogue = False
        while time.monotonic() < deadline:
            ending = s.sample('sigma-native-ending')
            rows.append(ending)
            if ending['mode'][0] != 6:
                break
            assert ending['players'][0]['hp'] == 0 and ending['players'][1]['hp'], ending
            if ending['blocked'] and not ending_dialogue:
                capture_pair(r, s.output / 'sigma-survivor-general-dialogue.png')
                ending_dialogue = True
            # The authored exit has steps. Jump through them, then confirm
            # the real General dialogue; do not teleport past its admission.
            r.input(0xdfff if ending['blocked'] else 0xbfdf, 1)
            time.sleep(.2)
            r.input(0xffff if ending['blocked'] else 0xffdf, 1)
            time.sleep(.5)
        else:
            raise AssertionError(('Surviving P2 did not reach the native ending', ending))
        assert ending['mode'][0] in (7, 9, 11), ('Victory reached a retry instead of ending progression', ending)
        capture_pair(r, s.output / 'sigma-native-ending.png')
        return dict(admission=admission, native_final_defeat=True, native_ending=ending)
    finally:
        r.release()
        (s.output / 'sigma-victory-series.json').write_text(json.dumps(rows, indent=2) + '\n')


def magma_entry_camera(s):
    from coop_fortress_followup_scenario import cameras
    r = s.r
    arrivals = []
    rows = []
    try:
        for owner in (1, 0):
            s.load(4, 1, 3)
            r.fixture(5, 3)
            s.wait('magma-approach-controls', lambda v: not v['blocked'] and
                   all(p['active'] and p['visible'] and p['hp'] and p['grounded'] and
                       p['action'] == 2 and not p['script'] and not p['door']
                       for p in v['players']), 25)
            r.input(0xffdf, owner)
            try:
                s.wait('magma-native-entry', lambda v: v['blocked'] or
                       any(p['script'] for p in v['players']), 15)
            finally:
                r.release()
            # Complete the first-visit text with real, fully released pad
            # pulses. Poll the native boss directly while advancing text;
            # the large presentation snapshot is unnecessary for each pulse.
            deadline = time.monotonic() + 65
            while time.monotonic() < deadline:
                bosses = [e for e in s.enemies() if e['type'] == 65]
                rows.append(dict(owner=owner, bosses=bosses))
                if bosses and bosses[0]['state'][0] == 1 and bosses[0]['state'][1] >= 3 and bosses[0]['hp'] >= 32:
                    break
                r.input(0xdfff, owner)
                time.sleep(.15)
                r.release()
                time.sleep(.15)
            else:
                raise AssertionError(('Dragoon first-visit introduction did not finish', owner, bosses))
            ready = s.wait('magma-fight-controls', lambda v: not v['blocked'] and not v['warning'] and
                           all(p['active'] and p['visible'] and p['hp'] and p['grounded'] and
                               p['action'] == 2 and not p['script'] and not p['door']
                               for p in v['players']), 25)
            ready['owner'] = owner
            ready['views'] = cameras(s)
            arrivals.append(ready)
            for camera in ready['views']:
                assert camera[0x24 // 2:0x28 // 2] == [5264, 5104], ('Dragoon intro enclosure was not released', ready)
                assert camera[0x48 // 2] & 255 == 4, ('Dragoon follow speed was not restored', ready)
            capture_pair(r, s.output / ('magma-fight-owner-' + str(owner) + '.png'))
        return dict(native_first_visit_introductions=True, released_cameras=arrivals)
    finally:
        r.release()
        (s.output / 'magma-entry-series.json').write_text(json.dumps(rows, indent=2) + '\n')


def cyber_air_door(s):
    return _air_door(s, 'cyber', 6, 1, 568, 2507, 1)


def spider_air_door(s):
    return _air_door(s, 'spider-air', 1, 4, 4152, 1435, 0)


def _air_door(s, label, stage, checkpoint, start_x, floor_y, air_index):
    from coop_fortress_followup_scenario import cameras
    r = s.r
    s.load(stage, 1, checkpoint)
    r.fixture(5, 0)
    # Grant only Jet Stingray's learned air dash to Zero. Marking every boss
    # defeated also skips Cyber's first-visit fight, invalidating recovery.
    # X instead needs the native foot armor prerequisite.
    if s.campaign == 0:
        r.write(0x801721c0 + 0x59, 0x10)
    r.fixture(7, 1, 0, 0 if s.campaign == 0 else 2)
    r.teleport_both(start_x, floor_y)
    s.wait(label + '-floor', lambda v: all(p['grounded'] for p in v['players']))
    records = []

    def doors():
        pool = r.read(0x80165a30, 32 * 0x8c)
        return [(0x80165a30 + i, struct.unpack_from('<h', pool, i + 10)[0])
                for i in range(0, len(pool), 0x8c) if pool[i] and pool[i + 1] == 8]

    def sample(label, actor):
        v = s.sample(label)
        v['body'] = [p.hex() for p in r.players()]
        v['door_actor'] = r.read(actor, 0x8c).hex()
        v['views'] = cameras(s)
        records.append(v)
        return v

    try:
        for index in (0, 1):
            before = s.sample(label + '-before-door')
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                available = [(a, x) for a, x in doors() if x > max(p['x'] for p in before['players'])]
                if available:
                    break
                time.sleep(.05)
            assert available, ('Native door placement did not appear', label, index, before)
            actor, x = min(available, key=lambda p: p[1])
            if index == air_index:
                # Set up on the already-entered corridor's real floor. The
                # jump/dash and door admission are actual controller actions.
                # Cyber covers its inner door. Spider matches the observed
                # outer-door entry with P1 at its native wall edge while
                # airborne P2 catches up, before shared scripted movement.
                r.teleport(0, x - (24 if stage == 1 else 12), floor_y)
                r.teleport(1, x - (82 if stage == 1 else 72), floor_y)
                s.wait(label + '-air-floor', lambda v: all(p['grounded'] for p in v['players']))
                sample(label + '-air-grounded', actor)
                if stage == 1:
                    r.input(0xffdf, 0)
                    time.sleep(.25)
                r.input(0xbfff if stage == 1 else 0xbfdf, 1)
                time.sleep(.1 if stage == 1 else .08)
                r.input(0xffff if stage == 1 else 0xffdf, 1)
                time.sleep(.067 if stage == 1 else .04)
                assert not r.players()[1][0x89] & 8, 'Jump did not leave the corridor floor'
                # Spider's recording holds Dash without Right. Right at the
                # wall enters native wall cling/slide before admission and
                # lands Zero, so it does not reproduce the airborne crush.
                r.input(0xdfff if stage == 1 else 0xdfdf, 1)
                if stage == 1:
                    r.input(0xffdf, 0)
            else:
                for seat in (0, 1):
                    r.input(0xffdf, seat)
            admitted = False
            airborne = False
            air_dashing = False
            suspended_air_entry = False
            closing = False
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                v = sample(label + '-door-' + str(index), actor)
                body = bytes.fromhex(v['door_actor'])
                airborne |= not v['players'][1]['grounded']
                air_dashing |= v['players'][1]['action'] == 13 and not v['players'][1]['grounded']
                passenger = bytes.fromhex(v['body'][1])
                suspended_air_entry |= (passenger[5] == 19 and passenger[0x67] == 255 and
                                        passenger[0xc4] == 255)
                if body[5] and not admitted:
                    admitted = True
                    if stage == 1 and index == air_index:
                        # Retain the recording's Circle-only input throughout
                        # the shared opening; P1 continues holding Right.
                        r.input(0xdfff, 1)
                    else:
                        r.release()
                assert all(p['hp'] for p in v['players']), ('Door killed a participant', index, v)
                closing |= admitted and (body[5] >= 4 or body[4] >= 2)
                if closing and all(not p['door'] for p in v['players']):
                    break
                time.sleep(.01)
            else:
                raise AssertionError(('Door did not finish', index, v))
            assert admitted and closing and (index != air_index or airborne and air_dashing)
            if stage == 1 and index == air_index:
                assert suspended_air_entry, 'Web fixture landed before admission; it cannot qualify the reported crush'
            r.release()
            capture_pair(r, s.output / (label + '-door-' + str(index) + '-closed.png'))
        s.watch_enemy = None
        ready = _native_dialogue_wait(s, label + '-fight', lambda v: not v['blocked'] and not v['warning'] and
                       any(e['hp'] >= 32 and e['state'][0] == 1 for e in s.enemies()) and
                       all(p['hp'] and p['grounded'] and p['action'] == 2 and not p['door'] and
                           not p['script'] for p in v['players']))
        ready['views'] = cameras(s)
        capture_pair(r, s.output / (label + '-air-door-fight.png'))
        return dict(outer_closed=True, inner_closed=True, airborne_door=air_index, fight=ready)
    finally:
        r.release()
        (s.output / (label + '-air-door-series.json')).write_text(json.dumps(records, indent=2) + '\n')
