"""Original-disc X1 character contract. Fixtures prepare positions/progress.

Native controller input drives movement, attacks and state restoration; no
fixture asserts a hit, damage result or successful movement transition.
"""
import json
import struct
import time
from coop_debug import capture_pair


def x1_buster_damage(s):
    """Prove damage through the original damage-store PC, not despawning."""
    r=s.r;results=[]
    def frames(count):
        first=r.request('mod_counters')['frame'];deadline=time.monotonic()+15
        while r.request('mod_counters')['frame']-first<count:
            if time.monotonic()>deadline:raise TimeoutError('Native damage probe stalled')
            time.sleep(.01)
    try:
        for seat in (0,1):
            s.load(1,0);r.fixture(5,3);r.teleport_both(500,427);r.teleport(seat,620,427)
            s.wait('x1-plant-open',lambda row:any(e['type']==12 and e['state'][1]>=3 for e in s.enemies()),12)
            r.input(0xffdf,seat);frames(2);r.release();frames(2)
            target=next(e for e in s.enemies()if e['type']==12 and abs(e['x']-704)<10)
            hp=0x13bed0+target['slot']*0x9c+0x5c
            r.request('wtrace_range',lo=hex(hp),hi=hex(hp+1));r.request('wtrace_clear')
            hits=[]
            for _ in range(6):
                r.input(0x7fff,seat);frames(5);r.release();frames(12)
                writes=r.request('wtrace_dump',count=4096)
                hits=[e for e in writes['entries']if int(e['pc'],16)==0x8002DF0C and
                      (int(e['new'],16)&127)<(int(e['old'],16)&127)]
                if hits:break
            assert hits,('No original damage-store evidence',seat,target,writes)
            capture_pair(r,s.output/('x1-damage-'+str(seat)+'.png'))
            results.append(dict(seat=seat,character=s.campaign^seat,target=target,hits=hits))
        return dict(actual_native_buster_damage=results)
    finally:
        r.release()
        (s.output/'x1-buster-damage.json').write_text(json.dumps(results,indent=2),encoding='utf-8')


def x1_characters(s):
    r=s.r
    rows=[]
    def frames(count):
        start=r.request('mod_counters')['frame'];deadline=time.monotonic()+15
        while r.request('mod_counters')['frame']-start<count:
            if time.monotonic()>deadline:raise TimeoutError('Native frame advance stopped')
            time.sleep(.01)
    def observe(label,capture=False):
        row=s.sample(label);row['bodyhex']=[p.hex()for p in r.players()]
        mirror=r.read(r.diagnostic()+0x480,128)
        row['p2_shots']=[list(mirror[i*8:i*8+8])for i in range(16)if mirror[i*8]]
        pool=r.read(r.diagnostic()+0x880,16*8)
        row['p1_shots']=[list(pool[i*8:i*8+8])for i in range(16)if pool[i*8]]
        assert [p['character']for p in row['players']]==[s.campaign,s.campaign^1],row
        assert all(p['hp']for p in row['players']),row
        rows.append(row)
        if capture:capture_pair(r,s.output/(label+'.png'))
        return row
    def hold(seat,buttons,count):
        r.input(buttons,seat);frames(count)
    def setup():
        s.load(1,0);r.fixture(5,3);r.teleport_both(500,427);r.teleport(1,560,427)
        s.wait('x1-both-grounded',lambda v:all(p['grounded']for p in v['players']),10);frames(45)
    try:
        for seat in (0,1):
            setup();before=observe('x1-idle-'+str(seat),True)
            hold(seat,0xffdf,12);run=observe('x1-run-'+str(seat),True);r.release();frames(12)
            assert run['players'][seat]['x']>before['players'][seat]['x']+10,run
            hold(seat,0xdfff,8);dash=observe('x1-dash-'+str(seat),True);r.release();frames(40)
            assert dash['players'][seat]['action']==12,dash
            hold(seat,0xbfff,6);jump=observe('x1-jump-'+str(seat),True);r.release();frames(1)
            hold(seat,0xdfff,3);air=observe('x1-air-dash-blocked-'+str(seat));r.release();frames(45)
            assert jump['players'][seat]['y']<dash['players'][seat]['y']-20,jump
            assert air['players'][seat]['action']!=13,air
            hold(seat,0x7fff,5);shot=observe('x1-buster-'+str(seat),True);r.release();frames(40)
            hold(seat,0xff7f,2);r.release();frames(3)
            hold(seat,0x7fff,100);charge=observe('x1-charge-'+str(seat),True);r.release();frames(12)
            released=observe('x1-charge-released-'+str(seat),True)
            assert bytes.fromhex(charge['bodyhex'][seat])[0x94]>0,charge
            assert any(p[1]==18 for p in released['p2_shots'if seat else'p1_shots']),released
            assert all(p[1]in(0,9,18)for p in shot['p2_shots'if seat else'p1_shots']),shot
            frames(60)
        # All X4 armor flags remain saved, but neither body gains those
        # capabilities. The two character packages override the active forms.
        r.fixture(7,s.campaign,0,2);setup();frames(3)
        assert r.read(0x80172207,2)==bytes((15,2))
        assert all(not p[0xa7]and not p[0xb8]for p in r.players())
        observe('x1-saved-armors-suppressed',True)
        r.fixture(7,s.campaign,1,1);frames(3)
        assert r.players()[s.campaign][0x93]==1,'X lost selected X4 boss weapon'
        hold(s.campaign,0x7fff,12);special=observe('x1-x4-boss-weapon',True);r.release()
        assert any(p[1]==1 for p in special['p2_shots'if s.campaign else'p1_shots']),special
        frames(40)
        for op in ('save','load'):
            generation=r.request('savestate_status')['generation']
            r.request('savestate',op=op,slot=10);deadline=time.monotonic()+20
            while time.monotonic()<deadline:
                status=r.request('savestate_status')
                if status['generation']!=generation and not status['pending']:
                    assert status['last_ok'],status;break
                time.sleep(.02)
            else:raise TimeoutError('X1 snapshot '+op+' did not complete')
        frames(3);observe('x1-restored',True)
        return dict(campaign=s.campaign,observations=len(rows),current_build_save_load=True)
    finally:
        r.release()
        (s.output/'x1-characters.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')


def x1_iris_buster(s):
    if s.campaign!=1:raise ValueError("Use --campaign 1 for the native Iris encounter")
    r=s.r;s.load(11,0,1);r.fixture(5,3)
    for seat in(0,1):r.input(0xffdf,seat)
    try:s.wait('iris-admitted',lambda row:any(e['type']==66 and e['hp']==48 for e in s.enemies()),90,True)
    finally:r.release()
    s.wait('iris-controls',lambda row:not row['blocked']and not row['warning']and all(p['state']==1 and not p['script']and not p['door']for p in row['players']),30,True)
    zero=s.campaign^1;rows=[];lowered=False;end=time.monotonic()+120
    while time.monotonic()<end:
        enemies=[]
        for e in s.enemies():
            if e['type']==66:
                e['variant']=r.read(0x8013bed0+e['slot']*0x9c+2,1)[0];enemies.append(e)
        rows.append(enemies)
        core=next((e for e in enemies if e['variant']==1),None)
        if core and core['hp']==0 and core['state'][0]>=2:break
        if core and not lowered:r.fixture(6,core['slot'],4);lowered=True
        target=core or next((e for e in enemies if e['variant']==0),None)
        if not target:time.sleep(.05);continue
        x=max(2080,min(2340,target['x']-60));y=max(120,min(442,target['y']+8))

        if r.read(0x801721dc,1)[0] or r.read(0x80141bdc,1)[0]:
            r.input(0xbfff,0);time.sleep(.06);r.release();time.sleep(.03);continue
        try:r.teleport(zero,int(x),int(y))
        except RuntimeError as error:
            if "Native fixture rejected" in str(error):continue
            raise
        r.input(0xffdf,zero);time.sleep(.035);r.release()
        r.input(0x7fff,zero);time.sleep(.10);r.release();time.sleep(.25)
    else:
        (s.output/'iris-series.json').write_text(json.dumps(rows,indent=2));raise AssertionError('Iris buster defeat did not complete')
    capture_pair(r,s.output/'iris-defeated.png');(s.output/'iris-series.json').write_text(json.dumps(rows,indent=2))
    counters=[c for c in r.request('mod_counters')['counters']if 'iris' in c['name']];print(json.dumps(counters),flush=True)
    assert lowered and any(c['name']=='mmx4.x1.iris-buster-hits'and c['count'] for c in counters),counters
    next_area=s.wait('x1-iris-native-next-area',lambda row:row['mode'][:2]==[6,0]and row['section']==1,120,True)
    return dict(native_armor_exposure=True,core_health_fixture=4,native_core_defeat=True,counters=counters,observations=len(rows),native_next_section=next_area["section"])
