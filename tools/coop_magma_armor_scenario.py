"""Native Dragoon upper entry with an armored partner on the lower route.

Fixtures select the authored Armor checkpoint and prepare observed positions.
Boarding, upper-route jumps, lower-route punches, boss admission, dismount,
departure/return, controls and the separate bottom-death check remain native.
"""
import json
import struct
import time

from coop_debug import capture_pair


def magma_armor_entry(s, leaders=(0, 1), check_pit=True):
    r = s.r
    s.watch_enemy = 65

    def vehicle(seat):
        return r.read(r.diagnostic()+(0x200 if seat else 0x620), 0xb0)

    def board(seat):
        s.load(4, 1, 2)
        r.fixture(5, 3)
        armor = vehicle(0)
        assert armor[0] and armor[1] == 1 and armor[5] == 0, armor.hex()
        x, y = struct.unpack_from('<ii', armor, 8)
        r.teleport(seat, x//65536, y//65536-70)
        s.wait('dragoon-native-armor-boarding', lambda v:
               r.players()[seat][0xc5] and vehicle(seat)[5] == 1, 15)

    cases = []
    for leader in leaders:
        rider = leader ^ 1
        prefix = f'dragoon-upper-p{leader+1}'
        board(rider)
        r.teleport(rider, 4943, 672)
        r.teleport(leader, 4833, 555)
        state = next(c['count'] for c in r.request('mod_counters')['counters']
                     if c['name'] == 'mmx4.coop.split-state')
        initial = s.wait(prefix+'-cameras-ready', lambda v: all(
            struct.unpack('<h', r.read(state+16+seat*252+10, 2))[0] > 4500
            for seat in (0, 1)), 20)
        capture_pair(r, s.output/(prefix+'-routes.png'))
        rows = []
        started = time.monotonic()
        reached_upper = False
        mounted_below = False
        try:
            while time.monotonic()-started < 90:
                v = s.sample(prefix+'-approach')
                rows.append(v)
                assert all(p['hp'] for p in v['players']), ('Route killed a hero', v)
                reached_upper |= v['players'][leader]['x'] > 4930 and v['players'][leader]['y'] < 480
                mounted_below |= (reached_upper and r.players()[rider][0xc5] != 0 and
                                  v['players'][rider]['x'] < 5150 and
                                  v['players'][rider]['y'] >= 660)
                fighting = any(e['hp'] == 48 and e['state'][0] == 1 and e['state'][1] >= 3
                               for e in v['enemies'])
                if (fighting
                        and not v['blocked'] and not v['warning'] and all(
                            p['visible'] and p['state'] == 1 and p['action'] == 2 and
                            p['grounded'] and not p['script'] for p in v['players'])):
                    break
                if fighting and not v['blocked'] and not v['warning']:
                    r.release()
                    time.sleep(.04)
                    continue
                elapsed = time.monotonic()-started
                pulse = int(elapsed*4) % 3 == 0
                if v['blocked'] or any(p['script'] for p in v['players']):
                    r.input(0xbfff if pulse else 0xffff, leader)
                    r.input(0xffff, rider)
                else:
                    r.input(0xbfdf if pulse else 0xffdf, leader)
                    r.input((0x7fdf if pulse else 0xffdf)
                            if elapsed > 1.3 and r.players()[rider][0xc5] else 0xffff, rider)
                time.sleep(.04)
            else:
                raise AssertionError(('Native Dragoon admission did not finish', v))
        finally:
            r.release()
            (s.output/(prefix+'-frames.json')).write_text(json.dumps(rows, indent=2)+'\n')
        assert reached_upper and mounted_below, 'The split-height armored approach was not exercised'
        assert not r.players()[rider][0xc5], 'Transported rider did not dismount'
        assert v['lives'] == initial['lives'], 'Admission consumed a shared life'
        capture_pair(r, s.output/(prefix+'-fight.png'))
        movements = []
        for seat in (0, 1):
            before = s.sample(prefix+'-control-before')['players'][seat]['x']
            r.input(0xff7f, seat)
            try:
                after = s.wait(prefix+'-control-after', lambda v:
                               v['players'][seat]['x'] < before-5, 3)
            finally:
                r.release()
            movements.append(after['players'][seat]['x']-before)
        cases.append(dict(leader=leader, rider=rider, minimum_hp=[
            min(v['players'][seat]['hp'] for v in rows) for seat in (0, 1)],
            native_boss=v['enemies'], players=v['players'], controls=movements))
    pit = None
    if check_pit:
        board(1)
        r.teleport(0, 4833, 555)
        # Below the actual lower room's bottom, not on its safe672 platform.
        # Do not set health/death flags: native Armor402C4 must still kill.
        r.teleport(1, 4943, 900)
        pit = s.wait('dragoon-armor-actual-bottom-death', lambda v:
                     not v['players'][1]['hp'] and v['players'][1]['state'] >= 2, 10)
        assert pit['players'][0]['hp'] > 0
        capture_pair(r, s.output/'dragoon-armor-bottom-death.png')
    return dict(native_armored_admissions=cases, lower_room_bottom_death=pit)
