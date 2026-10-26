"""Native Sigma forms1/2 defeats, survivor drop and final-fight admission.

Stage/position/weapon/protection/one-HP fixtures prepare the scenario. Actual
attacks must defeat each upper form; native floor collapse, falling, room
release and final boss initialization must follow. P1 dies before the second
defeat. No success flags, room limits or scene phases are set by the test.
"""
import json
import time
from coop_fortress_followup_scenario import cameras,retain


def sigma_phase3_survivor(s):
    r=s.r;s.load(12,1);r.fixture(5,3);r.fixture(7,s.campaign^1,0,1)
    r.teleport_both(704,420)
    end=time.monotonic()+65
    while time.monotonic()<end:
        row=s.sample('sigma12-approach')
        if not row['blocked'] and not row['warning'] and any(e['type']==68 and e['hp']==48 for e in s.enemies()):break
        for seat in (0,1):r.input(0xbfff if row['blocked'] or row['warning'] else 0xffdf,seat)
        time.sleep(.05)
        if row['blocked'] or row['warning']:r.release();time.sleep(.05)
    else:raise AssertionError('Native Sigma approach did not reach first fight')
    r.release()
    retain(s,'sigma12-before');boss=next(e for e in s.enemies() if e['type']==68)
    r.fixture(6,boss['slot'],1);zero=s.campaign^1;end=time.monotonic()+50
    while time.monotonic()<end:
        bosses=[e for e in s.enemies() if e['type']==68]
        if not bosses or any(e['hp']==0 and e['state'][0]>=2 for e in bosses):break
        boss=bosses[0];r.teleport(zero,max(1120,min(1380,int(boss['x']))),442)
        r.input(0xefef,zero);time.sleep(.15);r.release();time.sleep(.5)
    else:raise AssertionError('Native Sigma first-phase defeat was not reached')
    retain(s,'sigma12-first-defeat');r.release()
    end=time.monotonic()+45;rows=[]
    while time.monotonic()<end:
        row=s.sample('sigma12-sequel');row['enemies']=s.enemies();rows.append(row)
        if any(e['type']==68 and e['hp']==48 for e in row['enemies']) and not row['blocked'] and not row['warning']:break
        if row['blocked'] or row['warning']:
            for seat in (0,1):r.input(0xbfff,seat)
            time.sleep(.05);r.release()
        time.sleep(.05)
    (s.output/'sigma12-sequel.json').write_text(json.dumps(rows,indent=2))
    retain(s,'sigma12-sequel-ready')
    boss=next(e for e in s.enemies() if e['type']==68 and e['hp']==48)
    survivor=1;dead=0
    r.fixture(5,1<<survivor);r.fixture(2,dead,0x80)
    s.wait('sigma2-partner-dead',lambda v:not v['players'][dead]['hp'],15)
    r.fixture(6,boss['slot'],1);end=time.monotonic()+60
    while time.monotonic()<end:
        bosses=[e for e in s.enemies() if e['type']==68]
        if not bosses or any(e['hp']==0 and e['state'][0]>=2 for e in bosses):break
        boss=bosses[0];r.teleport(survivor,max(1120,min(1380,int(boss['x'])-25)),442 if not s.campaign else 443)
        r.input(0xffdf,survivor);time.sleep(.04);r.release()
        r.input(0x7fff,survivor);time.sleep(1.4 if s.campaign else .25);r.release();time.sleep(1)
    else:raise AssertionError('Native Sigma second-phase defeat was not reached')
    retain(s,'sigma2-survivor-defeat');rows=[];end=time.monotonic()+90
    while time.monotonic()<end:
        row=s.sample('sigma3-drop');row['enemies']=s.enemies();row['views']=cameras(s);rows.append(row)
        if not row['blocked'] and not row['warning'] and any(e['type']==74 and e['hp']>0 and e['state'][0]==1 for e in row['enemies']):break
        if row['blocked'] or row['warning']:r.input(0xbfff,survivor)
        else:r.input(0xffdf,survivor)
        time.sleep(.06);r.release()
    else:
        (s.output/'sigma3-drop-series.json').write_text(json.dumps(rows,indent=2));retain(s,'sigma3-stalled')
        raise AssertionError('Native final Sigma fight did not start after actual phase1/2 defeats and survivor drop')
    (s.output/'sigma3-drop-series.json').write_text(json.dumps(rows,indent=2));retain(s,'sigma3-after-drop')
    assert row['players'][dead]['hp']==0 and row['players'][survivor]['hp'] and row['players'][survivor]['y']>650,row
    r.release()
    ready=s.wait('sigma3-survivor-controls',lambda v:not v['blocked'] and not v['warning'] and
        v['players'][survivor]['state']==1 and v['players'][survivor]['action']==2 and
        v['players'][survivor]['grounded'] and not v['players'][survivor]['script'] and
        not v['players'][survivor]['door'],20)
    assert ready['players'][dead]['hp']==0 and ready['players'][survivor]['hp']==32,ready
    before=ready['players'][survivor]['x'];r.input(0xFFDF,survivor)
    try:moved=s.wait('sigma3-survivor-moves',lambda v:v['players'][survivor]['x']>before+8,5)
    finally:r.release()
    retain(s,'sigma3-final-controls')
    return dict(phase1_defeat=True,phase2_defeat=True,final_native_bosses=s.enemies(),
        survivor=survivor,corpse_preserved=True,health=ready['players'][survivor]['hp'],
        lives=ready['lives'],movement_pixels=moved['players'][survivor]['x']-before)
