"""Local Both-door review: prepared checkpoint, physical inputs, saved notes.

Use a disposable profile with slot9 reserved for this review. Preparation
selects the authored checkpoint and approach positions, never door/scene flags.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import time

from coop_debug import Runtime
from test_mmx4_coop_regressions import Scenarios


CHECKS = {
    'Walk through door': 'Press Enter/Options to resume. Hold Right on the keyboard '
        'and on the DualSense until both heroes pass the real door. Both should keep '
        'their walk/run animation during opening. Confirm actual closing, advance '
        'the boss dialogue with X/Cross, then jump with each hero after control returns.',
    'Dash through door': 'Restart the approach, then resume. Hold Right + S on the '
        'keyboard and Right + Circle on the DualSense. Both should retain an advancing '
        'native dash animation during opening. Continue through closing and the boss '
        'introduction; confirm that both heroes regain control.',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--port', type=int, default=18645)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    profile = args.profile.resolve()
    identity = hashlib.sha256((profile / 'MegaManX4Recomp.exe').read_bytes()).hexdigest()
    receipt_path = profile / 'door-review-setup.json'
    notes_path = profile / 'door-review-notes.json'
    r = Runtime(args.port, isolated_inputs=True)

    def state(op):
        generation = r.request('savestate_status')['generation']
        r.request('savestate', op=op, slot=9)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            status = r.request('savestate_status')
            if status['generation'] != generation and not status['pending']:
                assert status['last_ok'], status
                return
            time.sleep(.03)
        raise TimeoutError('Door review snapshot ' + op)

    if args.prepare_only:
        assert receipt_path.exists() or not list(
            (profile / 'saves/openbios').glob('*slot09.*')), 'Use a fresh review profile'
        scenario = Scenarios(r, profile, 0)
        try:
            scenario.load(1, 1, 5)
            r.fixture(5, 0)
            before = scenario.wait('review-ground', lambda row: all(
                p['grounded'] and p['action'] == 2 for p in row['players']), 15)
            pool = r.read(0x80165a30, 32 * 0x8c)
            doors = [struct.unpack_from('<h', pool, i + 10)[0]
                     for i in range(0, len(pool), 0x8c)
                     if pool[i] and pool[i + 1] == 8]
            door_x = min(x for x in doors if x > max(p['x'] for p in before['players']))
            y = int(before['players'][0]['y'])
            r.teleport_both(door_x - 64, y)
            r.teleport(1, door_x - 80, y)
            scenario.wait('review-ready', lambda row: all(
                p['grounded'] and p['hp'] for p in row['players']) and
                all(b[0x61] == 0 for b in r.players()), 15)
            r.input(0xfff7, 0)
            time.sleep(.16)
            r.release()
            scenario.wait('review-paused', lambda row: row['mode'][:2] == [6, 2]
                          and row['menu'][0] == 1 and row['menu'][1] < 3, 15)
            time.sleep(.2)
            state('save')
            receipt_path.write_text(json.dumps(dict(binary_sha256=identity,
                setup_version=1, slot=9, checkpoint=[1, 1, 5], door_x=door_x,
                damage_enabled=True, physical_controls='unverified until real input'),
                indent=2) + '\n')
        finally:
            Runtime(args.port).release()
        return

    receipt = json.loads(receipt_path.read_text())
    assert receipt['binary_sha256'] == identity and receipt['damage_enabled']
    import tkinter as tk
    from tkinter import ttk
    root = tk.Tk()
    root.title('Mega Man X4 - Door animation review')
    root.geometry('650x540')
    records = json.loads(notes_path.read_text()) if notes_path.exists() else {}
    current = records.setdefault(identity, {})
    selected = tk.StringVar(value=next(iter(CHECKS)))
    instructions = tk.StringVar()
    status = tk.StringVar(value='First approach is paused. Enter/Options resumes.')
    controls = tk.StringVar(value='Controls pending: while paused, tap keyboard Right, '
        'release, then tap DualSense Right. Each must affect only its own port.')
    panel = ttk.Frame(root, padding=14)
    panel.pack(fill='both', expand=True)
    ttk.Combobox(panel, textvariable=selected, values=list(CHECKS),
                 state='readonly').pack(fill='x')
    ttk.Label(panel, textvariable=instructions, wraplength=615).pack(fill='x', pady=10)
    ttk.Label(panel, text='P1 keyboard: arrows, S dash, X jump. '
              'P2 DualSense: D-pad/stick, Circle dash, Cross jump.',
              wraplength=615).pack(fill='x')
    ttk.Label(panel, textvariable=controls, wraplength=615).pack(fill='x', pady=10)
    note = tk.Text(panel, height=6, wrap='word')
    note.pack(fill='both', expand=True)

    def save():
        notes_path.write_text(json.dumps(records, indent=2) + '\n')

    def refresh(*_):
        instructions.set(CHECKS[selected.get()])
        note.delete('1.0', 'end')
        note.insert('1.0', current.get(selected.get(), {}).get('notes', ''))

    def record(result):
        current[selected.get()] = dict(result=result,
            notes=note.get('1.0', 'end').strip(), recorded_utc=time.time())
        save()
        status.set(selected.get() + ': ' + result + ' saved locally')

    def restart():
        try:
            state('load')
            Runtime(args.port).release()
            status.set('Approach restored and paused. Enter/Options resumes.')
        except Exception as error:
            status.set(str(error))

    # Read-only native SIO samples establish ownership from actual physical
    # input, rather than treating configured GUIDs or injected pads as proof.
    seen = set()
    samples = []
    last = None
    def poll_controls():
        nonlocal last
        try:
            pad = r.request('pad_status')
            buttons = tuple(int(pad['slot' + str(i)]['buttons'], 16) for i in (0, 1))
            physical = pad['override'] == -1 and pad['override_p2'] == -1
            if physical and r.read(0x801721c0, 2) == bytes([6, 2]):
                if buttons in ((0xffdf, 0xffff), (0xffff, 0xffdf)):
                    seen.add(0 if buttons[0] == 0xffdf else 1)
                    if buttons != last:
                        samples.append(dict(buttons=list(buttons), overrides=[-1, -1],
                                            time_utc=time.time()))
                    if seen == {0, 1}:
                        controls.set('Verified in this run: keyboard Right reached only P1; '
                                     'DualSense Right reached only P2.')
                        current['physical_controls'] = dict(result='Pass', samples=samples[-16:])
                        save()
                last = buttons
            if not pad['slot1']['connected']:
                controls.set('P2 is disconnected. Connect the DualSense, then verify both ports.')
        except Exception:
            status.set('Game unavailable. Close this panel when finished.')
        root.after(500, poll_controls)

    row = ttk.Frame(panel)
    row.pack(fill='x', pady=10)
    ttk.Button(row, text='Restart approach', command=restart).pack(side='left')
    for result in ('Pass', 'Fail', 'Deferred'):
        ttk.Button(row, text=result, command=lambda value=result: record(value)).pack(side='left', padx=4)
    ttk.Label(panel, textvariable=status, wraplength=615).pack(fill='x')
    selected.trace_add('write', refresh)
    refresh()
    root.after(500, poll_controls)
    root.mainloop()


if __name__ == '__main__':
    main()
