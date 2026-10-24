"""Original-disc probes for Thomu's Sigma/Magma 1.0.3 follow-up."""
import json
import struct
import time
from coop_debug import capture_pair


def cameras(s):
    state=next(c['count'] for c in s.r.request('mod_counters')['counters']
               if c['name']=='mmx4.coop.split-state')
    return [list(struct.unpack('<42h',s.r.read(state+16+seat*0xfc,0x54)))
            for seat in (0,1)]


def retain(s,label):
    row=s.sample(label)
    row['actors']=actors(s);row['views']=cameras(s)
    (s.output/(label+'.json')).write_text(json.dumps(row,indent=2))
    capture_pair(s.r,s.output/(label+'-composed.png'))
    return row


def tower_top(s,seat):
    # The native lower/upper return strips are only16 pixels tall. Move
    # upward through them before gravity crosses the opposite return strip.
    for attempt in range(8):
        s.r.teleport(seat,3944,2113)
        s.r.teleport(seat,3928,920)
        if cameras(s)[seat][0x2a//2]==736:break
    else:raise AssertionError('Lower tower camera area was not admitted')
    deadline=time.monotonic()+24
    while time.monotonic()<deadline:
        view=cameras(s)[seat]
        if view[0x24//2]==3856 and view[0x0e//2]<=736:return
        time.sleep(.05)
    raise AssertionError('Upper tower camera did not arrive')


def actors(s):
    pools = [(0x8013bed0, 48, 0x9c, 'enemy'),
             (0x8013f328, 32, 0x9c, 'secondary'),
             (0x80142f98, 32, 0x30, 'controller'),
             (0x80165a30, 32, 0x8c, 'general')]
    result = []
    for base, count, stride, kind in pools:
        data = s.r.read(base, count * stride)
        for i in range(count):
            p = data[i*stride:(i+1)*stride]
            if p[0]:
                result.append(dict(pool=kind, address=hex(base+i*stride), type=p[1],
                    flags=list(p[:8]), x=struct.unpack_from('<i', p, 8)[0]/65536,
                    y=struct.unpack_from('<i', p, 12)[0]/65536))
    return result


def fortress_probe(s):
    result = []
    for stage, section, checkpoints in [(10, 0, range(3)), (11, 0, [0]),
                                         (4, 0, [0]), (4, 1, range(4))]:
        for checkpoint in checkpoints:
            s.load(stage, section, checkpoint)
            s.r.fixture(5, 3)
            time.sleep(.3)
            row=s.sample(f'probe-{stage}-{section}-{checkpoint}', True)
            row['actors']=actors(s)
            result.append(row)
    return result


def sigma1_doors(s):
    r=s.r
    lead=s.victory_seat;trail=lead^1
    if trail==s.campaign and getattr(s,'ultimate_armor',False):
        r.fixture(7,trail,0,2)
    s.load(10,0,1)
    r.fixture(5,3)
    tower_top(s,lead)
    r.input(0xffdf,lead)
    try:
        s.wait('sigma1-leading-first-door',lambda v:v['players'][lead]['x']>=4130,12)
    finally:r.release()
    retain(s,'sigma1-leader-waits-first-door')
    nova_samples=[]
    if trail==s.campaign and getattr(s,'ultimate_armor',False):
        # X is the trailing hero in these cases. Unlocking the armor is a
        # prerequisite fixture; the attack and its global freeze are native.
        r.input(0xfdff,trail)
        deadline=time.monotonic()+1.4
        try:
            while time.monotonic()<deadline:
                bodies=r.players()
                if bodies[trail][5]==0x22:
                    row=retain(s,'sigma1-nova-'+str(len(nova_samples)))
                    nova_samples.append(row)
                time.sleep(.03)
        finally:r.release()
        assert nova_samples,'Native Nova Strike was not exercised'
        assert all(any(a['pool']=='general' and a['type']==8 and a['flags'][3]
                       and a['x']==4160 for a in row['actors']) for row in nova_samples), \
                       'Waiting door vanished during Nova Strike'
    tower_top(s,trail)
    r.input(0xffdf,trail)
    try:s.wait('sigma1-paired-opening',lambda v:any(p['door'] for p in v['players']),15)
    finally:r.release()
    r.input(0xffdf,lead)
    try:s.wait('sigma1-leading-vestibule',lambda v:v['players'][lead]['x']>4280,12)
    finally:r.release()
    before=retain(s,'sigma1-p2-inside-first-door')
    assert any(a['pool']=='general' and a['type']==8 and a['x']==4464 and a['flags'][3]
               for a in before['actors']), 'Second door vanished from the vestibule'
    # Position the trailing player beside the original ladder and use Down
    # to cross its real 928..944 return strip while the paired door is open.
    r.teleport(trail,3928,927);r.input(0xffbf,trail)
    try:time.sleep(.6)
    finally:r.release()
    after=retain(s,'sigma1-after-trailing-stair')
    assert after['players'][lead]['x']>4280, 'Stairs displaced the hero inside the door'
    assert after['views'][lead][0x24//2]>=4160, 'Stairs replaced the partner room bounds'
    tower_top(s,trail)
    r.input(0xffdf,trail)
    try:s.wait('sigma1-trailing-crosses-first',lambda v:v['players'][trail]['x']>4280 and
               not any(p['door'] for p in v['players']),15)
    finally:r.release()
    crossed=retain(s,'sigma1-first-door-crossed-after-retreat')
    assert all(p['active'] and p['visible'] and p['hp'] for p in crossed['players'])
    # Traverse the vestibule and the second physical door with native input.
    for seat in (lead,trail):r.input(0xffdf,seat)
    try:
        s.wait('sigma1-second-door-admission',lambda v:v['blocked'] or
               any(p['script'] for p in v['players']),20)
    finally:r.release()
    s.wait('sigma1-boss-controls',lambda v:v['mode'][:2]==[6,0] and not v['blocked'] and
           all(p['active'] and p['visible'] and p['hp'] and p['state']==1 and
               p['action']>=2 and not p['script'] and not p['door'] for p in v['players']),45,True)
    fight=retain(s,'sigma1-second-door-fight')
    assert fight['stage']==10 and fight['mode'][:2]==[6,0],fight
    assert all(p['active'] and p['visible'] and p['hp'] for p in fight['players'])
    bosses=[e for e in s.enemies() if e['hp']>=32]
    assert bosses,('Second door did not admit a living boss',s.enemies())
    return dict(leader=lead,stair_retreat_preserves_partner=True,first_door_recovered=True,
                second_door_fight=True,bosses=bosses,
                nova_samples=len(nova_samples),positions=[p['x'] for p in crossed['players']])


def magma_distant_entry(s):
    s.load(4,1,2);s.r.fixture(5,3)
    s.r.teleport(1,5080,400)
    time.sleep(.4)
    retain(s,'magma-p2-upper-before-entry')
    deadline=time.monotonic()+18
    while time.monotonic()<deadline:
        s.r.input(0xffdf,1);time.sleep(.08);s.r.release()
        row=s.sample('magma-approach')
        if row['blocked'] or any(p['script'] for p in row['players']):break
    else:raise AssertionError('Native Magma admission was not triggered')
    rows=[]
    deadline=time.monotonic()+35
    while time.monotonic()<deadline:
        row=s.sample('magma-entry');row['views']=cameras(s);rows.append(row)
        if row['stage']!=4 or row['section']!=1 or row['mode'][0]!=6:
            break
        if row['blocked']:
            for seat in (0,1):s.r.input(0xbfff,seat)
            time.sleep(.08);s.r.release()
        elif row['players'][1]['x']>5510:
            # Keep the leader off the right lava edge after the shared scene;
            # a native lethal floor must not be qualified as a safe return.
            s.r.input(0xff7f,1);time.sleep(.15);s.r.release()
        if not row['blocked'] and not row['warning'] and all(
            p['active'] and p['state']==1 and p['action']>=2 and
            not p['script'] and not p['door'] for p in row['players']):break
        time.sleep(.1)
    (s.output/'magma-entry-rows.json').write_text(json.dumps(rows,indent=2))
    final=retain(s,'magma-p2-upper-fight')
    (s.output/'magma-warp-counters.json').write_text(json.dumps(s.r.request('mod_counters'),indent=2))
    assert final['stage']==4 and final['section']==1 and final['mode'][:2]==[6,0], ('Magma admission left gameplay',final)
    assert final['checkpoint']==3, ('Magma checkpoint was not committed',final)
    assert all(p['active'] and p['visible'] and p['hp'] and p['state']==1 for p in final['players']), 'Magma passenger did not return'
    assert any(p['type']==65 and p['hp'] for p in s.enemies()), 'Magma boss fight did not remain active'
    assert rows[0]['camera'][5]>=4900, 'Magma pan began at the distant partner'
    return dict(checkpoint=final['checkpoint'],both_players_present=True)


def sigma2_lasers(s):
    results=[]
    for leader in (1,0):
        s.load(11,0,0);s.r.fixture(5,3)
        s.r.teleport(leader,1040,400)
        rows=[]
        for n in range(50):
            time.sleep(.1)
            row=s.sample('sigma2-laser-'+str(leader)+'-'+str(n))
            row['actors']=actors(s);rows.append(row)
            if n%10==0:capture_pair(s.r,s.output/(f'sigma2-laser-{leader}-{n}-composed.png'))
        (s.output/f'sigma2-lasers-{leader}.json').write_text(json.dumps(rows,indent=2))
        beams=[a for row in rows for a in row['actors'] if a['pool']=='secondary' and
               a['type']==36 and a['flags'][4]==1]
        assert len(beams)>10,('Cannon beams were not exercised',leader)
        assert {a['flags'][2] for a in beams}=={0,1},'Both beam directions were not exercised'
        assert all(700<a['x']<1600 for a in beams),('Beam used the waiting view',leader,beams)
        assert all(row['stage']==11 and row['mode'][:2]==[6,0] and
                   all(p['hp'] and p['state']==1 for p in row['players']) for row in rows)
        results.append(dict(leader=leader,beams=len(beams),directions=[0,1],
                            x_range=[min(a['x'] for a in beams),max(a['x'] for a in beams)]))
    return dict(native_emitter_origins=results)


def sigma_ladder_survivor(s):
    """Native upper return strip after the distant partner's void death."""
    r=s.r;lead=s.victory_seat;dead=lead^1
    s.load(10,0,1);r.fixture(5,3)
    tower_top(s,lead);r.input(0xffdf,lead)
    try:s.wait('survivor-before-door',lambda v:v['players'][lead]['x']>=4050,12)
    finally:r.release()
    before=retain(s,'ladder-waiting-before-death')
    assert before['players'][lead]['x']<4130,'Setup entered the first door'
    r.teleport(dead,1278,2280)
    s.wait('ladder-partner-dead',lambda v:not v['players'][dead]['hp'],8)
    retain(s,'ladder-after-partner-death')
    r.input(0xff7f,lead)
    try:s.wait('survivor-back-to-ladder',lambda v:v['players'][lead]['x']<=3929,10)
    finally:r.release()
    # Align the original return strip after native upper-area admission.
    # Down drives the original ladder/terrain controller; no bounds or
    # death/success flags are written by the fixture.
    r.teleport(lead,3928,927);r.input(0xffbf,lead);rows=[]
    try:
        for n in range(65):
            row=s.sample('survivor-ladder-'+str(n));row['views']=cameras(s);rows.append(row)
            p=row['players'][lead]
            if not p['hp'] or (p['grounded'] and p['y']>=1008):break
            time.sleep(.07)
    finally:
        r.release();(s.output/'survivor-ladder.json').write_text(json.dumps(rows,indent=2))
    final=retain(s,'survivor-ladder-landed');p=final['players'][lead]
    assert p['hp'] and p['grounded'] and p['y']>=1008,('Unsafe ladder descent',final)
    assert final['views'][lead][0x28//2]==2048 and final['views'][lead][7]>736, \
        'The upper camera enclosure did not release'
    assert not final['players'][dead]['hp'] and final['lives']==before['lives']
    return dict(leader=lead,landing_y=p['y'],hp=p['hp'],camera_y=final['views'][lead][7],
                target_bottom=final['views'][lead][0x28//2],dead_partner_preserved=True)


def magma_giga_death(s):
    results=[]
    for leader in (0,1):
        s.load(4,0,1);s.r.fixture(5,3)
        s.r.teleport(leader,4300,880)
        time.sleep(.4)
        rows=[];deadline=time.monotonic()+16;seen=False;moving=True
        s.r.input(0xffdf,leader)
        try:
            while time.monotonic()<deadline:
                row=s.sample('giga-'+str(leader));row['actors']=actors(s);rows.append(row)
                seen|=any(a['pool']=='enemy' and a['type']==51 for a in row['actors'])
                if row['players'][leader]['x']>=4500:
                    if moving:s.r.release();moving=False
                    if cameras(s)[leader][5]>=4300:break
                time.sleep(.05)
        finally:s.r.release()
        retain(s,'giga-leader-'+str(leader))
        (s.output/f'giga-leader-{leader}-timeline.json').write_text(json.dumps(rows,indent=2))
        results.append(dict(leader=leader,giga_spawned=seen,x=rows[-1]['players'][leader]['x']))
    assert all(row['giga_spawned'] for row in results),results
    return dict(cases=results)
