"""Exercise original Jungle boss-door traversal in a private development run.

Requires an already running co-op executable and original disc. Use a fresh
controller-only boot for each campaign. The bounded native load/checkpoint
fixture seeds the antechamber; optional player fatal requests test survivors.
No actor positions, door state, boss HP or completion flags are written.
"""
import argparse
import json
from pathlib import Path
import struct
import time

from coop_debug import Runtime


def body_state(body):
    x, y = struct.unpack_from('<ii', body, 8)
    return dict(active=body[0], visible=body[3], character=body[2], state=body[4], action=body[5],
                hp=body[0x5c] & 127, x=x/65536, y=y/65536,
                door=body[0xc4], script=body[0xc0], grounded=bool(body[0x89] & 8))


def snapshot(runtime):
    raw = runtime.read(runtime.diagnostic(), 0x464)
    if struct.unpack_from('<I', raw, 0x1c)[0] != 1:
        raise RuntimeError('This check requires canonical diagnostic snapshots')
    if struct.unpack_from('<I', raw, 12)[0]:
        raise RuntimeError('Co-op reported a failure')
    play = raw[0x400:0x464]
    return dict(frame=runtime.request('mod_counters')['frame'],
                mode=list(play[:4]), stage=play[12], section=play[13],
                checkpoint=play[0x1d], campaign=play[0x43], lives=play[0x44],
                blocked=play[0x1c],
                players=[body_state(raw[0x300:0x3e4]),
                         body_state(raw[0x100:0x1e4])],
                camera=list(struct.unpack('<12h', runtime.read(0x801419b0, 24))))


def run_case(runtime, campaign, owner, survivor, output, both=False):
    if both and not survivor:
        return run_paired_case(runtime, campaign, owner, output)
    name = f'campaign-{campaign}-owner-{owner}-survivor-{int(survivor)}'
    record = dict(name=name, owner=owner, survivor=survivor,
                  method='native checkpoint fixture; controller-only traversal')
    events = []
    try:
        runtime.release()
        runtime.fixture(1, 1, 1, campaign)
        runtime.wait_playable(60, advance_dialogue=True)
        runtime.fixture(3, 5)
        runtime.wait_playable(60, advance_dialogue=True)
        if survivor:
            runtime.fixture(2, owner ^ 1, 0x80)
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                state = snapshot(runtime)
                if state['players'][owner ^ 1]['state'] == 3:
                    break
                time.sleep(.05)
            else:
                raise TimeoutError('Original partner death did not finish')
        record['before'] = snapshot(runtime)
        before_lives = record['before']['lives']
        if both and not survivor:
            def wait_count():
                return sum(c['count'] for c in runtime.request('mod_counters')['counters']
                           if c['name']=='mmx4.coop.boss-door-waits')
            before_wait=wait_count()
            runtime.input(0xffdf,owner)
            deadline=time.monotonic()+15
            while time.monotonic()<deadline:
                state=snapshot(runtime);events.append(state)
                if state['blocked'] or any(p['door'] or p['script'] for p in state['players']):
                    raise AssertionError('Both-player door opened for the first player alone')
                if wait_count()>=before_wait+20:break
                time.sleep(.05)
            else:raise TimeoutError('First player never reached the waiting door')
            record['waiting']=state
            runtime.screenshot(output/(name+'-waiting.png'))
            runtime.input(0xffff,owner)
            runtime.input(0xffdf,owner^1)
            owner=0 # Both touch; native canonical player has deterministic priority.
        runtime.input(0xffdf, owner)
        entered = False
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            state = snapshot(runtime)
            events.append(state)
            player = state['players'][owner]
            if not player['hp'] or player['state'] >= 2:
                raise AssertionError('Door owner died during traversal')
            if player['door']:
                entered = True
                runtime.release()
            if entered and not player['door']:
                break
            time.sleep(.05)
        else:
            raise TimeoutError('Native door did not enter and finish')
        runtime.release()
        # Partner transport is committed on the next native player tick.
        time.sleep(.2)
        after = snapshot(runtime)
        record['after'] = after
        if after['campaign'] != campaign or after['lives'] != before_lives:
            raise AssertionError('Door altered campaign identity or shared lives')
        partner = after['players'][owner ^ 1]
        if survivor:
            if partner['hp'] or partner['state'] != 3:
                raise AssertionError('Door revived the fallen partner')
        # The next native boss conversation must finish before another load;
        # changing loader mode during that script leaves its gates unfinished.
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            state = snapshot(runtime)
            if not state['blocked'] and not state['players'][owner]['script']:
                break
            runtime.input(0xbfff, owner)
            time.sleep(.1)
            runtime.release()
            time.sleep(.1)
        else:
            raise TimeoutError('Native boss conversation did not release play')
        record['after_conversation'] = snapshot(runtime)
        if not survivor:
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                state = snapshot(runtime)
                partner = state['players'][owner ^ 1]
                if partner['active'] and partner['visible'] and partner['state'] == 1 and \
                        partner['action'] == 2 and partner['grounded']:
                    break
                time.sleep(.05)
            else:
                raise TimeoutError('Script passenger return animation did not finish grounded')
            record['after_return'] = state
            if not partner['hp'] or abs(partner['x'] - state['players'][owner]['x']) > 40:
                raise AssertionError('Living partner did not return beside the owner')
        runtime.screenshot(output / (name + '.png'))
        record['status'] = 'passed'
    except Exception as error:
        record['status'] = 'failed'
        record['error'] = str(error)
        try:
            record['failure_state'] = snapshot(runtime)
            runtime.screenshot(output / (name + '-failed.png'))
        except Exception as diagnostic_error:
            record['diagnostic_error'] = str(diagnostic_error)
    finally:
        runtime.release()
        (output / (name + '-events.json')).write_text(json.dumps(events, indent=2))
    return record


def run_paired_case(runtime, campaign, first, output):
    """Both-player admission must lead to a physical crossing, without beams."""
    name = f'campaign-{campaign}-owner-{first}-survivor-0'
    record = dict(name=name, owner=first, survivor=False,
                  method='native checkpoint; both-player physical door traversal')
    events = []

    def counters():
        return {c['name']: c['count'] for c in runtime.request('mod_counters')['counters']}

    def transport_count(counts):
        return sum(counts.get('mmx4.coop.' + key, 0)
                   for key in ('script-departures', 'room-departures'))

    def door_open():
        pool = runtime.read(0x80165a30, 32 * 0x8c)
        return any(pool[i + 1] == 8 and pool[i + 4] == 1 and pool[i + 5] == 3
                   for i in range(0, len(pool), 0x8c) if pool[i])

    def observe():
        state = snapshot(runtime)
        events.append(state)
        if any(not p['hp'] or not p['active'] or not p['visible']
               or p['state'] != 1 for p in state['players']):
            raise AssertionError('A paired-door participant vanished or died')
        if transport_count(counters()) != before_transport:
            raise AssertionError('Both-player door scheduled a partner teleport')
        if state['campaign'] != campaign or state['lives'] != before_lives:
            raise AssertionError('Paired door altered campaign or shared lives')
        return state

    try:
        runtime.release()
        runtime.fixture(1, 1, 1, campaign)
        runtime.wait_playable(60, advance_dialogue=True)
        runtime.fixture(3, 5)
        runtime.wait_playable(60, advance_dialogue=True)
        runtime.fixture(5, 3)
        record['before'] = snapshot(runtime)
        before_lives = record['before']['lives']
        before_counts = counters()
        before_transport = transport_count(before_counts)
        before_wait = before_counts.get('mmx4.coop.boss-door-waits', 0)
        runtime.input(0xffdf, first)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            state = observe()
            if state['blocked'] or any(p['door'] or p['script'] for p in state['players']):
                raise AssertionError('Paired door opened before the second player touched it')
            if counters().get('mmx4.coop.boss-door-waits', 0) >= before_wait + 20:
                break
            time.sleep(.05)
        else:
            raise TimeoutError('First player did not reach the waiting door')
        record['waiting'] = state
        for seat in (0, 1):
            runtime.input(0xffdf, seat)
        deadline = time.monotonic() + 30
        entered = False
        controlled = False
        while time.monotonic() < deadline:
            state = observe()
            entered |= any(p['door'] for p in state['players'])
            if not controlled and door_open():
                runtime.release()
                stopped = observe()
                end_frame = stopped['frame'] + 12
                while state['frame'] < end_frame:
                    state = observe()
                    time.sleep(.02)
                if any(state['players'][seat]['x'] <= stopped['players'][seat]['x'] + 3
                       for seat in (0, 1)):
                    raise AssertionError('Scripted door entry stopped when controls were released')
                record['released_controls'] = state
                for seat in (0, 1):
                    runtime.input(0x1f7f, seat)  # Left + jump + fire + dash.
                start = state
                end_frame = state['frame'] + 12
                while state['frame'] < end_frame:
                    state = observe()
                    time.sleep(.02)
                if any(state['players'][seat]['x'] <= start['players'][seat]['x'] + 3
                       or abs(state['players'][seat]['y'] - start['players'][seat]['y']) > 2
                       for seat in (0, 1)):
                    raise AssertionError('Player input escaped the scripted door entry')
                record['opposing_controls'] = state
                controlled = True
                runtime.release()
            crossed = counters().get('mmx4.coop.both-door-crossings', 0) > \
                before_counts.get('mmx4.coop.both-door-crossings', 0)
            if crossed and not any(p['door'] for p in state['players']):
                break
            time.sleep(.05)
        else:
            raise TimeoutError(f'Both players did not physically cross (entered={entered})')
        if not controlled:
            raise AssertionError('Native scripted door carry was not observed')
        runtime.release()
        record['after'] = observe()
        # Complete the native conversation and keep checking for a delayed
        # passenger departure after the actual door has finished.
        runtime.input(0xffdf, 0)
        runtime.input(0xffdf, 1)
        deadline = time.monotonic() + 45
        conversation = False
        while time.monotonic() < deadline:
            state = observe()
            locked = state['blocked'] or any(p['script'] for p in state['players'])
            if locked:
                conversation = True
                runtime.input(0xbfff, 0)
                time.sleep(.1)
                runtime.release()
                time.sleep(.1)
            elif conversation:
                break
            else:
                time.sleep(.05)
        else:
            raise TimeoutError('Native paired boss conversation did not enter and finish')
        record['after_conversation'] = observe()
        record['status'] = 'passed'
        runtime.screenshot(output / (name + '.png'))
    except Exception as error:
        record.update(status='failed', error=str(error))
        try:
            record['failure_state'] = snapshot(runtime)
            record['failure_players'] = [p.hex() for p in runtime.players()]
            record['failure_doors'] = runtime.read(0x80165a30, 32 * 0x8c).hex()
            record['failure_camera'] = runtime.read(0x801419b0, 0xfc).hex()
        except Exception as diagnostic_error:
            record['diagnostic_error'] = str(diagnostic_error)
    finally:
        runtime.release()
        (output / (name + '-events.json')).write_text(json.dumps(events, indent=2))
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=14725)
    parser.add_argument('--campaign', type=int, choices=(0, 1), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--boot', action='store_true')
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    runtime = Runtime(args.port)
    if args.boot:
        runtime.boot(campaign=args.campaign)
    results = []
    for survivor, owner in ((False, 0), (False, 1), (True, 0), (True, 1)):
        record = run_case(runtime, args.campaign, owner, survivor, output)
        results.append(record)
        (output / 'results.json').write_text(json.dumps(results, indent=2))
        print(json.dumps(record), flush=True)
        if record['status'] != 'passed':
            raise SystemExit(1)


if __name__ == '__main__':
    main()
