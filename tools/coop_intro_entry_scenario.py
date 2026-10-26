"""Native Eregion admissions with both heroes near the entrance.

Position/protection fixtures prepare the approach. Native spawning, WARNING,
the full introduction, passenger return and controller movement prove entry.
"""
import struct
import time

from coop_debug import capture_pair


def intro_near_entry(s):
    r = s.r
    results = []
    for leader in range(2):
        prefix = f"intro-near-p{leader + 1}"
        r.fixture(5, 3)
        s.load(0, 1)
        r.fixture(5, 3)
        r.wait_playable(timeout=50, advance_dialogue=True)
        r.teleport(0, 3936, 443 if not s.campaign else 442)
        r.teleport(1, 3936, 442 if not s.campaign else 443)
        s.watch_enemy = 8
        state = next(c["count"] for c in r.request("mod_counters")["counters"]
                     if c["name"] == "mmx4.coop.split-state")
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            v = s.sample(prefix + "-settling")
            assert all(p["hp"] for p in v["players"]), ("Invalid approach setup", v)
            if all(struct.unpack("<h", r.read(state + 16 + seat * 252 + 10, 2))[0] >= 3700
                   for seat in range(2)):
                break
            time.sleep(.1)
        else:
            raise AssertionError("Private cameras did not settle before approach")
        before = s.sample(prefix + "-before")
        minimum_hp = [p["hp"] for p in before["players"]]
        # Zero's campaign also runs its earlier native conversation here.
        deadline = time.monotonic() + 60
        try:
            while time.monotonic() < deadline:
                v = s.sample(prefix + "-approach")
                for seat, p in enumerate(v["players"]):
                    minimum_hp[seat] = min(minimum_hp[seat], p["hp"])
                enemies = [e for e in s.enemies() if e["type"] == 8]
                if (enemies and enemies[0]["hp"] == 48 and not v["blocked"]
                        and all(p["state"] == 1 and p["action"] == 2 and p["visible"]
                                and not p["script"] and not p["door"] for p in v["players"])):
                    break
                if v["blocked"]:
                    r.input(0xbfff, 0)
                    r.input(0xbfff, 1)
                    time.sleep(.04)
                    r.release()
                else:
                    r.input(0xdfdf if v["players"][leader]["x"] < 4530 else 0xffff, leader)
                    r.input(0xffdf if v["players"][leader ^ 1]["x"] < 4280 else 0xffff, leader ^ 1)
                time.sleep(.04)
            else:
                capture_pair(r, s.output / (prefix + "-stalled.png"))
                raise AssertionError("Nearby Eregion entry did not restore both heroes")
        finally:
            r.release()
        assert all(minimum_hp), ("A hero died during the introduction", minimum_hp)
        capture_pair(r, s.output / (prefix + "-fight.png"))
        controls = []
        for seat in range(2):
            start = s.sample(prefix + "-controls-before")
            r.input(0xff7f, seat)
            time.sleep(.2)
            r.release()
            time.sleep(.1)
            after = s.sample(prefix + "-controls-after")
            delta = after["players"][seat]["x"] - start["players"][seat]["x"]
            assert delta < -5, ("Native control was not restored", seat, delta, after)
            controls.append(dict(seat=seat, x_delta=delta))
        results.append(dict(leader=leader, before=before, fight=v,
                            minimum_hp=minimum_hp, controls=controls))
    return dict(admissions=results)
