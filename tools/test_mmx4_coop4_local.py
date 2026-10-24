"""Bounded native local 3/4-player split check, with isolated muted profiles."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import time

from coop_debug import Runtime, capture_pair

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--exe', type=Path, required=True)
parser.add_argument('--disc', type=Path, required=True)
parser.add_argument('--report-dir', type=Path, required=True)
parser.add_argument('--players', type=int, choices=(3, 4), default=4)
parser.add_argument('--port', type=int, default=17941)
parser.add_argument('--free-cutscenes', action='store_true')
args = parser.parse_args()
source = Path(__file__).resolve().parents[1]
exe = args.exe.resolve()
root = args.report_dir.resolve()
root.mkdir(parents=True, exist_ok=False)
for name in ('assets', 'mods', 'bios'):
    shutil.copytree(exe.parent / name, root / name)
for file in (exe, *exe.parent.glob('*.dll')):
    shutil.copy2(file, root / file.name)
state = 'format_version = 2\n[[feature]]\npackage_id = "mmx4.coop4"\nid = "coop"\nenabled = true\n'
if args.players == 3:
    state += '[feature.values]\np4 = "none"\n'
if args.free_cutscenes:
    state += '\n[[feature]]\npackage_id = "mmx4.coop-free-cutscenes"\nid = "free-cutscenes"\nenabled = true\n'
(root / 'mods/state.toml').write_text(state, encoding='utf-8')
config = (source / 'game.toml').read_text(encoding='utf-8').replace(
    'exe = "mmx4/SLUS_005.61"', 'exe = ' + json.dumps((source / 'mmx4/SLUS_005.61').as_posix()))
(root / 'game.toml').write_text(config, encoding='utf-8')
(root / 'settings.toml').write_text(
    '[video]\nfullscreen = false\nwindow_width = 960\ninternal_resolution = "native"\n[audio]\nvolume = 0\n', encoding='utf-8')
env = os.environ.copy()
for key, name in dict(TEMP='temp', TMP='temp', APPDATA='appdata', LOCALAPPDATA='local',
                      PSX_RESIDENT_CACHE='resident', PSX_OVERLAY_CACHE_DIR='overlay',
                      PSX_OVERLAY_CAPTURE_ROOT='captures', MESA_SHADER_CACHE_DIR='shaders').items():
    path = root / name
    path.mkdir(exist_ok=True)
    env[key] = str(path)
env.update(SDL_AUDIODRIVER='dummy', MMX4_RECOMP_DATA_DIR=str(root),
           PSX_OVERLAY_AUTOCOMPILE_OFF='1', PSX_RENDER_PASS_VERIFY='1',
           PSX_DEBUG_TOGGLES='0', PSX_DYNRES='0', PSX_INTERNAL_RESOLUTION='native')
runtime = Runtime(args.port)
report = {'players': args.players, 'executable_sha256': hashlib.sha256(exe.read_bytes()).hexdigest(), 'checks': []}


def save():
    (root / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


def sample(label):
    data = runtime.read(diagnostic, 0xdd0)
    header = struct.unpack_from('<6I', data)
    assert header[1] == args.players and not header[3], header
    players = []
    for seat in range(args.players):
        body = data[0x100 + seat * 256:0x1e4 + seat * 256]
        camera = data[0x500 + seat * 256:0x5fc + seat * 256]
        players.append(dict(character=body[2], state=body[4], pose=body[5], hp=body[0x5c] & 127,
                            x=struct.unpack_from('<i', body, 8)[0] / 65536,
                            y=struct.unpack_from('<i', body, 12)[0] / 65536,
                            camera_x=struct.unpack_from('<i', camera, 8)[0] / 65536))
    row = dict(label=label, header=header, players=players,
               menus=[list(data[0xd00+i*0x34:0xd34+i*0x34]) for i in range(args.players)],
               mode=list(runtime.read(0x801721c0, 2)))
    report['checks'].append(row)
    save()
    return row


def frames(count, timeout=30):
    start = struct.unpack('<I', runtime.read(diagnostic + 16, 4))[0]
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if struct.unpack('<I', runtime.read(diagnostic + 16, 4))[0] >= start + count:
            return
        time.sleep(.03)
    raise TimeoutError('Native simulation stopped')


def picture(label):
    capture_pair(runtime, root / (label + '.png'))


def native_fixture(command, seat, value):
    # Offline native damage grace isolates controller ownership from enemy
    # knockback. Door/death qualification must run without this fixture.
    def word(address, value):
        for byte in range(4):
            runtime.write(address+byte, (value >> (byte*8)) & 255)
    seq = struct.unpack('<I', runtime.read(diagnostic+0x30, 4))[0]+1
    for offset, item in ((0x34, command), (0x38, seat), (0x3c, value)):
        word(diagnostic+offset, item)
    word(diagnostic+0x30, seq)
    deadline = time.monotonic()+10
    while struct.unpack('<I', runtime.read(diagnostic+0x44, 4))[0] != seq:
        assert time.monotonic() < deadline, 'Offline protection was not acknowledged'
        time.sleep(.03)
    report['input_fixture'] = 'Native damage grace; no door/death claim'


command = [str(root / exe.name), '--hidden-window', '--no-launcher', '--renderer', 'opengl',
           '--debug-port', str(args.port), '--game', str(root / 'game.toml'),
           '--bios', str(root / 'bios/openbios.bin'), '--disc', str(args.disc.resolve()),
           '--memcard-dir', str(root / 'saves')]
with (root / 'runtime.log').open('wb') as log:
    process = subprocess.Popen(command, cwd=root, env=env, stdout=log, stderr=log,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    try:
        deadline = time.monotonic() + 100
        while True:
            assert process.poll() is None, 'Runtime exited'
            try:
                runtime.request('get_registers')
                break
            except OSError:
                if time.monotonic() > deadline:
                    raise
                time.sleep(.1)
        diagnostic = next(c['count'] for c in runtime.request('mod_counters')['counters']
                          if c['name'] == 'mmx4.coop4.diagnostic-address')
        runtime.request('turbo', enabled=1)
        runtime.boot(wait_for_coop=False)
        runtime.request('turbo', enabled=0)
        deadline = time.monotonic() + 30
        while True:
            row = sample('enrolling')
            if row['header'][2] and all(p['state'] == 1 and p['hp'] for p in row['players']):
                break
            if time.monotonic() > deadline:
                raise TimeoutError('Native intro did not enroll all seats')
            time.sleep(.15)
        frames(12)
        deadline = time.monotonic() + 20
        while any(p['pose'] < 2 for p in sample('arrival')['players']):
            if time.monotonic() > deadline:
                raise TimeoutError('Concurrent native arrivals did not finish')
            time.sleep(.05)
        picture('spawn')
        native_fixture(3, 0, (1 << args.players)-1)
        for seat in range(args.players):
            before = sample('before-seat-' + str(seat + 1))
            runtime.input(0xffdf, seat)
            frames(20)
            runtime.input(0xffff, seat)
            frames(6)
            after = sample('seat-' + str(seat + 1) + '-moved')
            assert after['players'][seat]['x'] > before['players'][seat]['x'] + 15, (seat, before, after)
            for other in range(args.players):
                if other != seat:
                    assert abs(after['players'][other]['x'] - before['players'][other]['x']) < 2, (seat, other)
            runtime.input(0x7fff, seat)
            frames(8)
            runtime.input(0xffff, seat)
            frames(8)
        picture('all-seats-moved')
        leader = args.players - 1
        runtime.input(0xffdf, leader)
        frames(140)
        runtime.input(0xffff, leader)
        frames(8)
        apart = sample('last-seat-leading')
        assert apart['players'][leader]['x'] - apart['players'][0]['x'] > 250, apart
        assert apart['players'][leader]['camera_x'] - apart['players'][0]['camera_x'] > 200, apart
        assert all(p['hp'] for p in apart['players']), apart
        picture('independent-cameras')
        runtime.request('window_size', w=1280, h=720)
        frames(10)
        picture('resized')
        runtime.request('render_pass_refuse', on=1)
        try:
            time.sleep(.3)
            picture('refused-shared-fallback')
        finally:
            runtime.request('render_pass_refuse', on=0)
        frames(8)
        for seat in range(args.players):
            native_fixture(4, seat, 16)
        runtime.input(0xfff7, leader)
        time.sleep(.2)
        runtime.input(0xffff, leader)
        deadline = time.monotonic() + 8
        while runtime.read(0x801721c0, 2) != bytes([6, 2]):
            if time.monotonic() > deadline:
                raise TimeoutError('Pause did not open')
            time.sleep(.05)
        deadline = time.monotonic() + 30
        while True:
            paused = sample('private-pause-initializing')
            if all(m[4] == 1 for m in paused['menus']):
                break
            if time.monotonic() > deadline:
                raise TimeoutError('Private menus did not initialize')
            time.sleep(.05)
        picture('private-pause')
        # X starts in the weapon column; an unupgraded Zero starts on
        # the horizontal tank row. Use an available native neighbor.
        for seat in range(args.players):
            before = sample('menu-before-' + str(seat+1))
            runtime.input(0xffdf if before['players'][seat]['character'] else 0xffbf, seat)
            time.sleep(.15)
            runtime.input(0xffff, seat)
            time.sleep(.15)
            after = sample('menu-after-' + str(seat+1))
            assert after['menus'][seat][0x14] != before['menus'][seat][0x14], (seat, before, after)
            for other in range(args.players):
                if other != seat:
                    assert after['menus'][other][0x14] == before['menus'][other][0x14], (seat, other)
        picture('independent-menu-cursors')
        deadline = time.monotonic() + 30
        while runtime.read(0x801721c0, 2) != bytes([6, 0]):
            if time.monotonic() > deadline:
                raise TimeoutError('Pause did not close')
            runtime.input(0xfff7)
            time.sleep(.2)
            runtime.input()
            time.sleep(.3)
        frames(8)
        picture('resumed')
        stats = runtime.request('render_pass_stats')
        counters = {c['name']: c['count'] for c in runtime.request('mod_counters')['counters']}
        grid = runtime.request('stereo_stats')
        report.update(render_stats=stats, counters=counters, grid=grid,
                      presents=runtime.request('gl_present_ring', n=20))
        assert counters.get('mmx4.coop4.local-grid-committed', 0) > 10, counters
        assert counters.get('mmx4.renderer.activated') == 1, counters
        assert all(counters.get(f'mmx4.renderer.layer{i}-tiles', 0) > 0 for i in range(3)), counters
        assert not counters.get('mmx4.renderer.arena-failed', 0), counters
        assert runtime.request('gpu_state')['ws']['nw_extra'] == 0
        assert not counters.get('mmx4.coop4.local-view-state-leak', 0), counters
        assert stats['verify_checks'] > 0 and not any(stats[k] for k in
            ('verify_mismatch', 'aborted', 'watchdog', 'vram_leaks')), stats
        assert grid['published']['mode'] == 3 and grid['published']['valid'], grid
        for event in report['presents']['events']:
            _, _, w, h = event[5]
            assert abs(w * 6 - h * 8) <= 8, event
        if args.free_cutscenes:
            from coop_four_cutscene_scenario import four_cutscene
            report['cutscene'] = four_cutscene(runtime, diagnostic, args.players, root)
        report['passed'] = True
        save()
        print('Native local split passed:', args.players, 'players', flush=True)
    except BaseException as error:
        try:
            sample('failure')
            report['render_stats'] = runtime.request('render_pass_stats')
        except (OSError, RuntimeError):
            pass
        report.update(passed=False, error=repr(error))
        save()
        raise
    finally:
        if process.poll() is None:
            process.terminate()
        process.wait(timeout=15)
