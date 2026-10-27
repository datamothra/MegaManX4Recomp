"""Require identical real-GPU results from conservative and batched builds."""
import re
import subprocess
import sys


def run(exe, args):
    print('GPU comparison:', exe, args or ['atlas'], flush=True)
    result = subprocess.run([exe, *args], capture_output=True, text=True,
                            timeout=90, encoding='utf-8', errors='replace')
    if result.returncode == 77:
        return None
    print(result.stdout[-1600:], end='', flush=True)
    assert result.returncode == 0, (result.returncode, result.stderr[-4000:])
    assert re.search(r'^checks=\d+ failures=0$', result.stdout, re.M), result.stdout
    values = dict(re.findall(r'^(atlas|rb|digest|hires|wide)=([0-9a-f]{16})$',
                             result.stdout, re.M))
    expected = {'rb', 'digest', 'hires', 'wide'} if args else {'atlas'}
    assert values.keys() == expected, values
    return values


def main():
    lle, hle = sys.argv[1:]
    cases = [[]] + [[str(scale), str(worker), '80', dynamic, 'latched']
                   for scale in (1, 4) for worker in (0, 1)
                   for dynamic in ('fixed', 'dynres')
                   if scale > 1 or dynamic == 'fixed']
    for index, args in enumerate(cases):
        reference, candidate = run(lle, args), run(hle, args)
        if index == 0 and reference is None and candidate is None:
            return 77
        assert reference is not None and candidate is not None, 'Unexpected GPU skip'
        assert reference == candidate, (args, reference, candidate)
        print('LLE/HLE pixels and readbacks match:', args or ['atlas'])
    # Preserve the shared fixture's adversarial mid-frame background-latch
    # changes as a recording/replay check. Its incomplete wide center before
    # a frame policy changes is batch-dependent; it is not a cross-tier
    # image oracle (gpu_gl_renderer.c: wide_fast_center_valid).
    for exe in (lle, hle):
        for scale in (1, 4):
            dynamic = 'dynres' if scale > 1 else 'fixed'
            direct = run(exe, [str(scale), '0', '80', dynamic])
            worker = run(exe, [str(scale), '1', '80', dynamic])
            assert direct is not None and direct == worker, (exe, scale, direct, worker)
            print('Adversarial worker replay matches:', exe, scale)
    return 0


if __name__ == '__main__':
    sys.exit(main())
