"""Native standalone Zero slashes against Double in either campaign.

The story helper reaches Double through native doors, including Iris first for
Zero's campaign. Health/position/invulnerability fixtures prepare combat;
real isolated saber input must damage Double. No admission or defeat flags
are supplied. The native DD04 health writer records the actual attack class.
"""
import json
import time
from coop_fortress_followup_scenario import retain
from coop_story_scenarios import story_bosses


def double_standing(s):
    r=s.r;observations=[]
    def observe(kind,index):
        if kind!=73:return
        zero=s.campaign^1
        boss=next(e for e in s.enemies() if e['type']==73)
        initial=boss['hp'];address=0x8013BED0+boss['slot']*0x9C
        r.fixture(5,3)
        r.request('wtrace_range',lo=hex(address+0x5C),hi=hex(address+0x5D))
        r.request('wtrace_clear')
        for attempt in range(10):
            target=next(e for e in s.enemies() if e['type']==73)
            r.teleport(zero,max(2080,min(2340,int(target['x'])-25)),442)
            r.input(0xFFDF,zero);time.sleep(.04);r.release();time.sleep(.15)
            before=next(e for e in s.enemies() if e['type']==73)
            # A long neutral gap prevents a second/third combo slash from
            # satisfying a test specifically about the first standing cut.
            r.input(0x7FFF,zero);time.sleep(.25);r.release();time.sleep(1.15)
            after=next(e for e in s.enemies() if e['type']==73)
            observations.append(dict(attempt=attempt,before=before,after=after))
        trace=r.request('wtrace_dump',count=4096)
        (s.output/'double-standing-health-writes.json').write_text(json.dumps(trace,indent=2))
        hits=[e for e in trace['entries'] if e['pc']=='0x8002DF0C' and
              int(e['a2'],16)==24 and e['old']!=e['new']]
        final=next(e for e in s.enemies() if e['type']==73)
        (s.output/'double-standing-attempts.json').write_text(json.dumps(observations,indent=2))
        retain(s,'double-standing-final')
        assert final['hp']<initial,('Standalone standing slash did not damage Double',observations)
        assert hits,('No native type24 damaging health write observed',trace)
        assert all(p['hp'] for p in s.sample('double-standing-survival')['players'])
        observations.append(dict(initial_hp=initial,final_hp=final['hp'],native_type24_health_writes=len(hits),zero_seat=zero))
        return True
    s.story_boss_observer=observe
    try:sequence=story_bosses(s)
    finally:del s.story_boss_observer
    assert observations,'Double was not reached'
    return dict(standing=observations[-1],story_approach=sequence)
