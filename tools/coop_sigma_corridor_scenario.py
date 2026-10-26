"""Sigma2 outer-door camera lock and native story-boss admission.

Stage/position/view fixtures bypass earlier traversal. The 1744 corridor
destination and all physical door/script/admission states remain native.
"""
import json
import time
from coop_fortress_followup_scenario import cameras
from coop_debug import capture_pair

def corridor_crossing(s,leader):
    r=s.r;rows=[]
    prefix=f'leader-{leader}-'
    def record(label):
        row=s.sample(label);row['views']=cameras(s);rows.append(row)
        return row
    try:
        s.load(11,0);r.fixture(5,3)
        time.sleep(1)
        s.wait('initial-controls',lambda v:v['stage']==11 and v['mode'][:2]==[6,0] and not v['blocked']and not v['warning']and all(p['action']==2 and p['state']==1 for p in v['players']),25)
        # Prepare the observed platform/camera together while native Pause
        # stops physics. The entrance limits remain the original 256..1440;
        # neither door state nor the tested 1744 lock is written by setup.
        r.input(0xfff7,0);time.sleep(.15);r.release()
        s.wait('setup-paused',lambda v:v['mode'][:2]==[6,2] and v['menu'][0]==1,10)
        time.sleep(.5)
        r.teleport(leader,1716,331 if leader==s.campaign else 330)
        r.teleport(leader^1,1713,331 if (leader^1)==s.campaign else 330)
        split=next(c['count']for c in r.request('mod_counters')['counters']if c['name']=='mmx4.coop.split-state')
        for camera in(0x801419b0,split+16,split+16+0xfc):
            for offset in(8,20):
                for byte in range(4):r.write(camera+offset+byte,((1440<<16)>>(byte*8))&255)
        r.input(0xfff7,0);time.sleep(.15);r.release()
        s.wait('setup-resumed',lambda v:v['mode'][:2]==[6,0],10)
        s.wait('positions-installed',lambda v:all(p['x']>=1680 and p['hp']for p in v['players']),10)
        floor=s.wait('pre-door-ground',lambda v:all(p['grounded']and p['hp']for p in v['players']),12)
        assert all(328<=p['y']<=332 for p in floor['players']),floor
        record('before-door');capture_pair(r,s.output/(prefix+'before-door.png'))
        deadline=time.monotonic()+20
        for seat in(0,1):r.input(0xffdf,seat)
        try:
            while time.monotonic()<deadline:
                row=record('crossing')
                assert all(p['hp'] and p['state']==1 for p in row['players']),row
                if all(p['x']>=1790 for p in row['players']):break
                time.sleep(.04)
            else:raise TimeoutError(('Both players did not pass the native outer door',row))
        finally:r.release()
        s.wait('physical-gates-released',lambda v:all(not p['door']for p in v['players']),15)
        time.sleep(1.5)
        settled=record('corridor-settled');capture_pair(r,s.output/(prefix+'corridor-settled.png'))
        assert all(v[0x24//2:0x28//2]==[1744,1744]for v in settled['views']),('Corridor horizontal targets differ',settled)
        assert all(v[10//2]==1744 for v in settled['views']),('Private camera did not pan to the corridor lock',settled)
        kind=66 if s.campaign else 73
        for seat in(0,1):r.input(0xffdf,seat)
        try:s.wait('native-boss-admission',lambda v:any(e['type']==kind and e['hp']==48 for e in s.enemies()),120,True)
        finally:r.release()
        s.wait('native-fight-controls',lambda v:not v['blocked']and not v['warning']and all(p['active']and p['visible']and p['state']==1 and not p['door']and not p['script']for p in v['players']),30,True)
        admitted=record('boss-admitted');capture_pair(r,s.output/(prefix+'boss-admitted.png'))
        assert admitted['lives']==floor['lives']and all(p['hp']==floor['players'][i]['hp']for i,p in enumerate(admitted['players'])),(floor,admitted)
        return dict(leader=leader,campaign=s.campaign,boss=kind,corridor=settled,admitted=admitted,prior_stage_traversal='bypassed by stage/position fixtures; both real doors and native scene required')
    finally:
        r.release();(s.output/(prefix+'camera-transitions.json')).write_text(json.dumps(rows,indent=2)+'\n')

def sigma_story_corridor(s):
    return dict(leaders=[corridor_crossing(s,leader)for leader in(0,1)])
