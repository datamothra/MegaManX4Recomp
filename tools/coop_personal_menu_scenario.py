"""Native controller-driven personal menu / tank checks, local or delay-sync.

Fixtures only prepare health, campaign abilities and acquired tank energy.
Navigation, healing and weapon selection run in the original executable.
"""
import json
import time


def personal_menus(s, capture=None):
    if getattr(s,'simultaneous_menus',True):
        from coop_simultaneous_menu_scenario import simultaneous_menus
        return simultaneous_menus(s,capture)
    r = s.r
    r.fixture(5, 3)
    s.load(1, 0)
    r.fixture(5, 3)
    r.fixture(7, s.campaign ^ 1, 0, 1)
    private = getattr(s, 'separate_etanks', False)
    r.fixture(6, 252, 16, 2)
    results = []

    def shot(label):
        if capture:
            capture(label)
        else:
            s.sample(label, True)

    def pulse(buttons, seat):
        r.input(buttons, seat); time.sleep(.16)
        r.release(); time.sleep(.16)

    def energy():
        return list(r.read(r.diagnostic()+0x45c, 2))

    def open_menu(seat, label):
        pulse(0xfff7, seat)
        row = s.wait(label, lambda v:v['mode'][:2] == [6, 2] and
                     v['menu'][0] == 1 and v['menu'][1] < 3, 10)
        time.sleep(.2)
        menu = list(r.read(0x801754a0, 0x34))
        character = s.campaign ^ seat
        # Zero's initializer explicitly clears slot9 (MENU+1F); X enables
        # it for Twin Slasher. Slot8 is unused/stale in Zero's native menu.
        assert menu[31] == (0 if character else 1), (character, menu)
        # The running menu legitimately projects PLAY+43. Observe the
        # completed canonical mirror, not a mid-call guest RAM read.
        assert r.read(r.diagnostic()+0x443, 1)[0] == s.campaign, 'Guest menu changed campaign'
        shot(label)
        return row

    def close_menu(seat, label):
        pulse(0xfff7, seat)
        s.wait(label, lambda v:v['mode'][:2] == [6, 0], 10)
        time.sleep(.2)

    for seat in (1, 0):
        r.fixture(2, seat, 16)
        before = s.sample('tank-before-'+str(seat))
        canonical = energy()
        open_menu(seat, 'personal-menu-'+str(seat))
        # Only its owner controls the native menu; the partner's Start must
        # not steal it. Either owner can open and cancel the native Quit popup.
        pulse(0xfff7, seat ^ 1)
        assert list(r.read(0x801721c0, 2)) == [6, 2]
        if seat:
            pulse(0xfffe, seat)
            s.wait('p2-native-quit',lambda v:v['menu']==[1,6],10)
            time.sleep(.8);pulse(0xbfff,seat)
            s.wait('p2-native-quit-cancelled',lambda v:v['menu'][0]==1 and v['menu'][1]<3,10)
        choices = []
        for _ in range(12):
            selected = r.read(0x801754b4, 1)[0]; choices.append(selected)
            if selected == 10:
                break
            pulse(0xffbf if selected < 10 else 0xff7f, seat)
        else:
            raise AssertionError(('E-tank not reachable with native D-pad', choices))
        shot('tank-selected-'+str(seat))
        pulse(0xbfff, seat)
        s.wait('tank-native-refill-'+str(seat), lambda v:v['menu'][0] == 1 and
               v['menu'][1] < 3, 12)
        time.sleep(.3)
        shot('tank-used-'+str(seat))
        close_menu(seat, 'tank-resumed-'+str(seat))
        after = s.sample('tank-after-'+str(seat), True)
        assert after['players'][seat]['hp'] == 32, after
        assert after['players'][seat ^ 1]['hp'] == before['players'][seat ^ 1]['hp'], (before, after)
        # Retail consumes the selected full tank, then compacts tank2 into
        # tank1. Check that native result inside only the owner's supply.
        expected = canonical[:] if private and seat else [canonical[1], canonical[1] & 128]
        assert energy() == expected, (private, seat, canonical, energy(), expected)
        # Reopening regenerates the correct menu after the other character
        # has used the shared graphics pages. Contents also survive exit.
        open_menu(seat ^ 1, 'other-character-after-tank-'+str(seat))
        close_menu(seat ^ 1, 'other-character-resumed-'+str(seat))
        results.append(dict(seat=seat, choices=choices, before=before,
                            after=after, canonical_before=canonical, canonical_after=energy()))

    if private:
        # P2's second full tank must survive a native stage reload even
        # after P1 has no energy. Healing again proves the guest's retained
        # contents were restored, rather than merely drawing a private icon.
        r.fixture(6, 252, 0, 0)
        s.load(1, 0)
        r.fixture(5, 3)
        r.fixture(2, 1, 16)
        open_menu(1, 'guest-tank-after-stage-reload')
        for _ in range(12):
            selected = r.read(0x801754b4, 1)[0]
            if selected == 10:
                break
            pulse(0xffbf if selected < 10 else 0xff7f, 1)
        else:
            raise AssertionError('Guest retained tank not selectable')
        pulse(0xbfff, 1); time.sleep(.5)
        s.wait('guest-retained-tank-used', lambda v:v['menu'][0] == 1 and v['menu'][1] < 3, 12)
        close_menu(1, 'guest-retained-tank-resumed')
        row = s.sample('guest-retained-tank-after', True)
        assert row['players'][1]['hp'] == 32 and energy() == [128, 128], row

    # X's selected weapon is personal in either campaign. Native menu
    # confirmation must change X only. Capture the first post-menu attack.
    xseat = s.campaign
    open_menu(xseat, 'x-weapon-menu')
    for _ in range(8):
        if r.read(0x801754b4, 1)[0] == 2:
            break
        pulse(0xffbf, xseat)
    else:
        raise AssertionError('Lightning Web not reachable')
    pulse(0xbfff, xseat)
    close_menu(xseat, 'weapon-resumed')
    mirror = r.read(r.diagnostic(), 0x400)
    bodies = [mirror[at:at+0xe4] for at in (0x300, 0x100)]
    assert bodies[xseat][0x93] == 1 and bodies[xseat ^ 1][0x93] == 0, [b[0x93] for b in bodies]
    r.input(0x7fff, xseat); time.sleep(.18); r.release()
    shot('x-weapon-after-resume')
    assert r.read(r.diagnostic()+0x443, 1)[0] == s.campaign
    result = dict(private_etanks=private, campaign=s.campaign, native_tank_uses=results,
                  character_menu_flags=True, owner_only_input=True, p2_quit_confirmation=True,
                  x_weapon_selection=True, guest_energy_survives_stage_reload=private)
    (s.output/'personal-menu-results.json').write_text(json.dumps(result, indent=2))
    return result
