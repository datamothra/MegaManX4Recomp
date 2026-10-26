"""Original-disc Double/Iris encounters for the private regression runner."""
import time


def story_bosses(s):
    def enemies(kind):
        result = [e for e in s.enemies() if e['type'] == kind]
        for e in result:
            e['variant'] = s.r.read(0x8013bed0 + e['slot'] * 0x9c + 2, 1)[0]
        return result

    def defeat(kind):
        # Use X's charged attack for Double. Iris's armor exposes a separate
        # core after saber hits; only that core loses real HP.
        seat = s.campaign if kind == 73 else s.campaign ^ 1
        lowered = set()
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            foes = enemies(kind)
            if any(e['hp'] == 0 and e['state'][0] == 2 for e in foes):
                return
            assert foes, 'Boss disappeared before a native defeat'
            boss = next((e for e in foes if e['variant']), foes[0])
            key = boss['slot'], boss['variant']
            if key not in lowered and (kind == 73 or boss['variant']):
                s.r.fixture(6, boss['slot'], 1)
                lowered.add(key)
            x = max(2080, min(2340, boss['x'] - (70 if kind == 73 else 24)))
            s.r.teleport(seat, x, min(443 if kind == 73 else 442, boss['y']))
            s.r.input(0xffdf, seat)
            time.sleep(.025)
            s.r.release()
            s.r.input(0x7fff, seat)
            time.sleep(1.4 if kind == 73 else .12)
            s.r.release()
            time.sleep(.4 if kind == 73 else .12)
        raise AssertionError(('Native attack did not defeat boss', enemies(kind)))

    s.load(11, 0, 1)
    before = s.sample('story-before')
    rounds = [66, 73] if s.campaign else [73, 66]
    if not s.both_story_bosses:
        rounds = rounds[:1]
    for index, kind in enumerate(rounds):
        s.watch_enemy = kind
        for seat in (0,1):s.r.input(0xffdf,seat)
        try:
            s.wait('story-ready', lambda _: any(e['hp'] == 48 for e in enemies(kind)), 120, True)
        finally:
            s.r.release()
        s.wait('story-controls', lambda r: not r['blocked'] and not r['warning'] and
               all(p['active'] and p['visible'] and p['state'] == 1 and p['action'] == 2 and
                   not p['door'] and not p['script'] for p in r['players']), 25, True)
        s.sample('story-fight-' + str(index), True)
        observer=getattr(s,'story_boss_observer',None)
        if observer is not None and observer(kind,index):
            return dict(observed_rounds=rounds[:index+1],completed_rounds=rounds[:index])
        defeat(kind)
        if index + 1 < len(rounds):
            s.wait('story-sequel', lambda r: r['mode'][0] == 4 or
                   (r['mode'][0] == 6 and r['players'][0]['x'] < 2000), 120, True)
            s.r.wait_playable(35, advance_dialogue=True)
            row = s.sample('story-second-door', True)
            assert row['checkpoint'] == 1 and row['lives'] == before['lives'], row
        else:
            # Double's post-battle speech is long, especially under TCP
            # instrumentation. Let native text finish; never clear its flags.
            row = s.wait('story-return', lambda r: r['mode'][0] == 10 or r['section'] == 1, 120, True)
        assert row['campaign'] == s.campaign and row['lives'] == before['lives'], row
    counts = {c['name']: c['count'] for c in s.r.request('mod_counters')['counters'] if 'story' in c['name']}
    assert counts.get('mmx4.coop.second-story-encounter', 0) == int(s.both_story_bosses), counts
    if s.both_story_bosses:
        assert counts['mmx4.coop.story-boss-defeated'] == 2, counts
    return dict(rounds=rounds, counters=counts, returned=row)
