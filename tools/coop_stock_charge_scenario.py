"""X's native stock-shot producer and personal HUD in a private QA process."""
import struct
import time
from coop_debug import capture_pair


def stock_charge_hud(self):
    r=self.r
    original=r.read(0x80172207,2)
    seat=self.campaign  # X is P2 in Zero's campaign.
    images=[]
    observations=[]

    def frame():
        return struct.unpack('<I',r.read(r.diagnostic()+4,4))[0]

    def observe(label):
        bodies=r.players()
        particles=r.read(0x80173ca0,64*0x60)
        actors=[]
        for slot in range(64):
            body=particles[slot*0x60:(slot+1)*0x60]
            if body[0] and body[1]==0x36:
                actors.append(dict(address=hex(0x80173ca0+slot*0x60),
                    visible=body[3],state=body[4],frame=body[0x47],
                    layer=body[0x14],xy=[struct.unpack_from('<h',body,10)[0],
                                        struct.unpack_from('<h',body,14)[0]],
                    assembly=hex(struct.unpack_from('<I',body,0x3c)[0])))
        row=dict(label=label,frame=frame(),stocks=[body[0xA6] for body in bodies],
            characters=[body[2] for body in bodies],hp=[body[0x5c]&127 for body in bodies],
            actors=actors)
        assert row['characters']==[self.campaign,self.campaign^1],row
        assert all(row['hp']),row
        observations.append(row)
        return row

    def advance(count,label):
        start=frame();deadline=time.monotonic()+20
        while frame()-start<count:
            if time.monotonic()>=deadline:raise TimeoutError(label)
            time.sleep(.02)
        return observe(label)

    def picture(label):
        path=self.output/(label+'.png')
        if getattr(self,'capture_composed',False):capture_pair(r,path)
        else:r.screenshot(path)
        images.append(str(path))

    def counters():
        return {c['name']:c['count'] for c in r.request('mod_counters')['counters']}

    try:
        # This fixture grants the authored stock-charge arm. Actual charging,
        # stock production and consumption below use native controller input.
        r.write(0x80172207,15);r.write(0x80172208,1)
        self.load(1,0)
        r.fixture(5,3)
        r.teleport_both(500,427);r.teleport(1,556,427)
        self.wait('stock-hud-both-grounded',lambda row:all(
            p['grounded'] for p in row['players']),10)
        r.fixture(7,seat,0,0)
        initial=advance(8,'stock-hud-before-charge')
        assert initial['stocks'][seat]==0,initial
        assert len(initial['actors'])==1,initial
        picture('stock-hud-empty')
        before=counters()
        r.input(0x7fff,seat)
        advance(210,'stock-hud-charge-held')
        r.release()
        charged=advance(12,'stock-hud-native-stock')
        assert charged['stocks'][seat]>0,('Native charge did not produce stock',observations)
        assert charged['stocks'][seat^1]==initial['stocks'][seat^1],observations
        assert charged['actors'][0]['visible'] and charged['actors'][0]['frame']==31-charged['stocks'][seat],charged
        picture('stock-hud-charged')
        after=counters()
        key='mmx4.coop.p%d-stored-charge-hud-draws'%(seat+1)
        assert after.get(key,0)>before.get(key,0),(key,before,after)
        if seat:
            assert after.get('mmx4.coop.p2-stored-charge-hud-ticks',0)>before.get('mmx4.coop.p2-stored-charge-hud-ticks',0),after
        if r.request('stereo_stats')['published']['mode']==2:
            assert after.get('mmx4.coop.stored-charge-hud-other-view-hidden',0)>before.get('mmx4.coop.stored-charge-hud-other-view-hidden',0),after
        # Fire the stored shots. Native input must consume the stock and hide
        # the one owner's indicator without changing Zero's unrelated byte.
        for index in range(8):
            if not observe('stock-hud-before-fire-%d'%index)['stocks'][seat]:break
            r.input(0x7fff,seat);advance(3,'stock-hud-fire-%d'%index)
            r.release();advance(15,'stock-hud-release-%d'%index)
        empty=advance(8,'stock-hud-consumed')
        assert empty['stocks'][seat]==0 and not empty['actors'][0]['visible'],empty
        assert empty['stocks'][seat^1]==initial['stocks'][seat^1],observations
        picture('stock-hud-consumed')
        stats=r.request('render_pass_stats')
        assert not any(stats.get(key,0) for key in ('verify_mismatch','aborted','watchdog','vram_leaks')),stats
        assert not after.get('mmx4.coop.local-view-state-leak',0),after
        return dict(x_seat=seat,native_stock_production=True,native_stock_consumption=True,
            original_charge=charged['stocks'][seat],observations=observations,pictures=images,
            counters=after,render_pass=stats)
    finally:
        r.release()
        r.write(0x80172207,original[0]);r.write(0x80172208,original[1])
