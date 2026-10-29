"""Audit the three authored falling-object bee emissions, not static placements."""
import json,time
from coop_debug import capture_pair
from coop_fortress_followup_scenario import cameras,actors


def intro_bees(s, *, leaders=(1,0), variants=(1,10,11), continue_approach=False):
    results=[];r=s.r
    for leader in leaders:
        for variant,start,threshold,expected in ((1,560,592,{703}),(10,2970,3040,{3167,3296}),(11,3260,3296,{3423})):
            if variant not in variants:continue
            s.load(0,1,0 if variant==1 else 1);r.fixture(5,3)
            r.teleport(leader,start,300 if variant==1 else 230)
            time.sleep(1)
            r.request('wtrace_disarm_all');r.request('wtrace_arm',lo='0x8013bed0',hi='0x8013dc10');r.request('wtrace_clear')
            rows=[];writes=[];seen=set();deadline=time.monotonic()+18;last=-1
            try:
                while time.monotonic()<deadline:
                    r.input(0xbfdf,leader)
                    time.sleep(.08);r.release();time.sleep(.04)
                    row=s.sample(f'bees-{leader}-{variant}');row['actors']=actors(s);rows.append(row)
                    data=r.request('wtrace_dump',count=128,pc_lo='0x800BF3B0',pc_hi='0x800BF4E4')
                    for e in data['entries']:
                        if e['seq']<=last:continue
                        if e['pc'] in ('0x800BF3D0','0x800BF408','0x800BF418'):
                            writes.append(e)
                            if e['pc']=='0x800BF408':seen.add(int(e['new'],16)&65535)
                    last=max(last,data.get('total',0)-1)
                    assert row['stage']==0 and row['section']==1 and row['players'][leader]['hp'],row
                    if expected<=seen:break
            finally:r.release();r.request('wtrace_disarm_all')
            spawned={int(e['addr'],16)+0x80000000-1 for e in writes if e['pc']=='0x800BF3D0'}
            visible=[];deadline=time.monotonic()+4
            while spawned and time.monotonic()<deadline:
                if continue_approach:
                    r.input(0xbfdf,leader);time.sleep(.12);r.release()
                time.sleep(.05)
                row=s.sample(f'bees-visible-{leader}-{variant}');row['actors']=actors(s);rows.append(row)
                visible.extend(a for a in row['actors'] if int(a['address'],16) in spawned and
                               a['pool']=='enemy' and a['type']==7 and a['flags'][3] and a['flags'][4]==1)
                if len(visible)>=4:break
            stem=f'bees-{leader}-{variant}'
            (s.output/(stem+'.json')).write_text(json.dumps(dict(rows=rows,emission_writes=writes),indent=2))
            capture_pair(r,s.output/(stem+'-composed.png'))
            assert expected<=seen,('Native flying group was not emitted',leader,variant,seen,row)
            assert visible,('Emitted bees did not remain drawable for their leader',leader,variant,spawned)
            results.append(dict(leader=leader,variant=variant,native_spawn_x=sorted(seen),threshold=threshold,drawable_samples=len(visible)))
    return dict(falling_object_flying_groups=results)
