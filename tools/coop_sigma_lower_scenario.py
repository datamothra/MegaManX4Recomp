"""Early Sigma2 lower-route drop, followed by an actual pit death.

Stage/checkpoint and contact-protection fixtures prepare the approach. Hold
Right through native arrival to exercise the upper camera area's still-easing
floor; waiting for an idle playable frame can hide the reported failure.
No camera limits, terrain flags, death state or room success flags are set.
"""
import json
import time
from coop_fortress_followup_scenario import cameras, retain


def sigma_lower_route(s):
    r=s.r;results=[]
    for leader in (1,0):
        s.load(11,1);r.fixture(5,3)
        lives=s.sample('sigma-lower-before-retry')['lives']
        r.fixture(3,1);r.input(0xFFDF,leader)
        rows=[];released=False;arrived=False;end=time.monotonic()+25
        try:
            while time.monotonic()<end:
                row=s.sample('sigma-lower-drop');row['views']=cameras(s);rows.append(row)
                p=row['players'][leader]
                if row['mode'][:2]==[6,0] and row['checkpoint']==1:
                    if p['state']==1 and p['action']>=2:
                        arrived=True
                        assert p['hp']==32,('False lower-route death',row)
                    if p['x']>=1118 and not released:r.release();released=True
                    if arrived and released and p['grounded'] and p['y']>700:break
                time.sleep(.005)
            else:raise AssertionError('Native early drop did not land on the lower platform')
        finally:
            r.release()
            (s.output/f'sigma-lower-{leader}-series.json').write_text(json.dumps(rows,indent=2))
        landing=retain(s,f'sigma-lower-{leader}-landing')
        assert all(p['hp']==32 for p in landing['players']) and landing['lives']==lives,landing
        waiter=leader^1
        assert landing['players'][waiter]['x']==(1056 if leader else 1080),landing
        assert landing['players'][waiter]['y']<500,landing
        # Walk off the actual lower platform. Contact protection must never
        # turn this correction into immunity to native pit deaths.
        r.input(0xFFDF,leader)
        try:
            dead=s.wait('sigma-lower-real-pit',lambda v:not v['players'][leader]['hp'],12)
        finally:r.release()
        assert dead['players'][waiter]['hp']==32 and dead['lives']==lives,dead
        retain(s,f'sigma-lower-{leader}-real-pit')
        results.append(dict(leader=leader,landing=landing,pit=dead,real_pit_lethal=True))
    return dict(campaign=s.campaign,cases=results)
