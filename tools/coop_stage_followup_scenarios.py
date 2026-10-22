"""Original-disc checks for the renewed 1.0.2 stage reports.

These prepare native checkpoints, positions, abilities and invulnerability.
Enemy-health setup shortens Tentoroid, but controller attacks supply the final
hit and original death/retirement code releases the room. Cannon probes hold
positions while observing original beam spawns; they do not qualify traversal.
No event-completion flag, collision tile or room limit is written by the tests.
"""

import json
import struct
import time

from coop_debug import capture_pair


def _actor_pools(r):
    result = {}
    for name, base, stride, count in [
        ("enemy", 0x8013BED0, 0x9C, 48),
        ("secondary", 0x8013F328, 0x9C, 32),
        ("effect", 0x8013E510, 0x70, 32),
        ("mote", 0x80165A30, 0x8C, 32),
        ("beam", 0x801435B0, 0x60, 32),
        ("train", 0x80169CB8, 0x30, 4),
    ]:
        data = r.read(base, stride * count)
        result[name] = [
            dict(
                slot=i,
                type=p[1],
                subtype=p[2],
                phase=list(p[4:8]),
                layer=p[0x14],
                x=struct.unpack_from("<i", p, 8)[0] / 65536,
                y=struct.unpack_from("<i", p, 12)[0] / 65536,
                raw=p.hex(),
            )
            for i in range(count)
            if (p := data[i * stride : (i + 1) * stride])[0]
        ]
    return result


def _camera_views(r):
    state = next(
        c["count"]
        for c in r.request("mod_counters")["counters"]
        if c["name"] == "mmx4.coop.split-state"
    )
    data = r.read(state + 16, 504)
    return [
        dict(
            x=struct.unpack_from("<h", data, n * 252 + 10)[0],
            y=struct.unpack_from("<h", data, n * 252 + 14)[0],
            enabled=data[n * 252 + 0x44],
            bounds=list(struct.unpack_from("<4h", data, n * 252 + 0x24)),
        )
        for n in range(2)
    ]


def slash_midboss_entry(s):
    r = s.r
    cases = []
    rows = []
    try:
        for owner, dead in [(1, False), (1, True), (0, False)]:
            s.load(8, 0, 2)
            time.sleep(1)
            r.wait_playable(45, advance_dialogue=True)
            r.fixture(5, 3)
            s.wait(
                "slash-checkpoint-both-ready",
                lambda v: all(
                    p["active"]
                    and p["visible"]
                    and p["hp"] == 32
                    and p["state"] == 1
                    and p["action"] == 2
                    for p in v["players"]
                )
                and abs(v["players"][0]["x"] - 6464) < 2
                and not v["blocked"],
                20,
            )
            if dead:
                r.fixture(2, 0, 0x80)
                s.wait(
                    "slash-p1-dead",
                    lambda v: v["players"][0]["state"] == 3
                    and v["players"][0]["hp"] == 0,
                    15,
                )
            tag = "%d-%d" % (owner, dead)
            r.teleport(owner, 6976, 362 if (s.campaign ^ owner) else 363)
            time.sleep(4)
            before = s.sample("slash-before-midboss-" + tag, True)
            r.input(0xFFDF, owner)
            try:
                admitted = s.wait(
                    "slash-midboss-admitted-" + tag,
                    lambda v: any(e["type"] == 45 for e in s.enemies()),
                    15,
                )
            finally:
                r.release()
            active = s.wait(
                "slash-midboss-controls-" + tag,
                lambda v: not v["blocked"]
                and not v["warning"]
                and any(
                    e["type"] == 45 and e["hp"] > 1 and e["state"][0] == 1
                    for e in s.enemies()
                )
                and all(
                    p["active"]
                    and p["visible"]
                    and p["state"] == 1
                    and p["action"] == 2
                    and p["hp"] == 32
                    and not p["script"]
                    and not p["door"]
                    for i, p in enumerate(v["players"])
                    if not (dead and i == 0)
                ),
                30,
                True,
            )
            if dead:
                assert active["players"][0]["hp"] == 0
            x = active["players"][owner]["x"]
            r.input(0xFF7F, owner)
            time.sleep(0.2)
            r.release()
            controlled = s.sample("slash-midboss-movement-" + tag)
            assert controlled["players"][owner]["x"] < x - 5, (
                "Midboss controls not restored",
                controlled,
            )
            capture_pair(r, s.output / ("slash-midboss-live-" + tag + ".png"))
            row = dict(
                owner=owner,
                p1_dead=dead,
                before=before,
                admitted=admitted,
                active=active,
                controlled=controlled,
                pools=_actor_pools(r),
            )
            cases.append(row)
            rows.append(row)
            (s.output / "slash-midboss-observations.json").write_text(
                json.dumps(rows, indent=2)
            )
        return dict(native_midboss_controls=cases)
    finally:
        r.release()


def slash_cannon_origins(s):
    r = s.r
    s.load(8, 0)
    r.fixture(5, 3)
    rows = []
    observed = []
    try:
        for x, y in [(1568, 240), (4320, 240)]:
            r.teleport(1, x, y)
            time.sleep(2)
            assert all(
                p["hp"] > 0 for p in s.sample("laser-safe-position")["players"]
            ), "Unsafe cannon fixture"
            found = 0
            deadline = time.monotonic() + 16
            while time.monotonic() < deadline:
                v = s.sample("slash-lasers-%d-%d" % (x, found))
                v["pools"] = _actor_pools(r)
                rows.append(v)
                assert all(p["hp"] > 0 for p in v["players"])
                enemies = {
                    0x8013BED0 + e["slot"] * 0x9C: e for e in v["pools"]["enemy"]
                }
                beams = [
                    (
                        a,
                        enemies.get(
                            struct.unpack_from("<I", bytes.fromhex(a["raw"]), 0x7C)[0]
                        ),
                    )
                    for a in v["pools"]["secondary"]
                    if a["type"] == 20
                ]
                beams = [(a, p) for a, p in beams if p and abs(p["x"] - x) < 300]
                if beams:
                    if not found:
                        capture_pair(r, s.output / ("slash-laser-live-%d.png" % x))
                    found += 1
                    observed += [
                        dict(
                            player_x=v["players"][0]["x"],
                            beam_x=a["x"],
                            parent_x=p["x"],
                            offset=a["x"] - p["x"],
                        )
                        for a, p in beams
                    ]
                    if found >= 3:
                        break
                time.sleep(0.1)
            assert found, ("No native beam observed", x)
        return dict(
            native_cannon_samples=observed,
            observed_emitters=len({round(v["parent_x"] / 100) * 100 for v in observed}),
        )
    finally:
        r.release()
        (s.output / "slash-laser-observations.json").write_text(
            json.dumps(rows, indent=2)
        )


def mushroom_midboss_exit(s):
    results = []
    output = s.output
    try:
        for dead in (False, True):
            s.output = output / ("mushroom-survivor" if dead else "mushroom-both-alive")
            s.output.mkdir()
            results.append(_mushroom_midboss_exit(s, dead))
    finally:
        s.output = output
    return dict(native_room_releases=results)


def _mushroom_midboss_exit(s, p1_dead):
    r = s.r
    rows = []

    def sample(label, shot=False):
        v = s.sample(label)
        if shot:
            capture_pair(r, s.output / (label + ".png"))
        v["views"] = _camera_views(r)
        v["enemies"] = s.enemies()
        rows.append(v)
        (s.output / "mushroom-midboss-observations.json").write_text(
            json.dumps(rows, indent=2)
        )
        return v

    try:
        s.load(3, 0, 3)
        r.fixture(5, 3)
        time.sleep(1)
        r.wait_playable(45, advance_dialogue=True)
        if p1_dead:
            r.fixture(2, 0, 0x80)
            s.wait(
                "mushroom-p1-dead",
                lambda v: v["players"][0]["state"] == 3 and v["players"][0]["hp"] == 0,
                15,
            )
        sample("mushroom-start", True)
        r.fixture(7, s.campaign ^ 1, 0, 1)
        r.teleport(1, 4880, 620)
        time.sleep(1)
        r.input(0xFFFF, 1)
        s.wait(
            "mushroom-native-midboss-admission",
            lambda v: any(
                e["type"] == 33 and e["state"][0] == 1 and e["hp"] > 1
                for e in s.enemies()
            )
            and not v["blocked"]
            and v["players"][1]["action"] >= 2,
            30,
            True,
        )
        r.release()
        sample("mushroom-midboss-active", True)
        for boss in s.enemies():
            if boss["type"] == 33 and boss["hp"] > 1:
                r.fixture(6, boss["slot"], 1)
        deadline = time.monotonic() + 35
        while time.monotonic() < deadline:
            boss = next(
                (e for e in s.enemies() if e["type"] == 33 and e["state"][0] == 1), None
            )
            if not boss:
                break
            player = s.sample("mushroom-attacker")["players"][1]
            if abs(player["x"] - boss["x"]) > 56:
                # Prepare a real saber contact at the observed safe upper
                # floor; never set a hit, death state or completion flag.
                r.teleport(1, max(4640, min(4880, int(boss["x"]) + 32)), 620)
                time.sleep(0.2)
            r.input(0x7FFF, 1)
            time.sleep(0.18)
            r.release()
            time.sleep(0.15)
        else:
            raise TimeoutError("Mushroom midboss native final hit not delivered")
        s.wait(
            "mushroom-midboss-retired",
            lambda v: not any(e["type"] == 33 for e in s.enemies()),
            25,
        )
        sample("mushroom-midboss-retired", True)
        # Exit progresses left after the native fight. Retain native terrain/jumps.
        for n in range(32):
            r.input(0xBF7F, 1)
            time.sleep(0.18)
            r.input(0xFF7F, 1)
            time.sleep(0.32)
            r.release()
            time.sleep(0.1)
            v = sample("mushroom-after-midboss-%d" % n, n % 3 == 0)
            if v["section"] == 1:
                break
            if p1_dead and v["players"][1]["x"] < 4500:
                break
        if v["section"] == 1:
            v = s.wait(
                "mushroom-section2-ready",
                lambda v: v["section"] == 1
                and all(
                    p["active"]
                    and p["visible"]
                    and p["hp"] == 32
                    and p["state"] == 1
                    and p["action"] == 2
                    for p in v["players"]
                ),
                35,
            )
            v = sample("mushroom-native-section2", True)
        assert v["players"][1]["hp"] == 32, v
        assert v["players"][0]["hp"] == (0 if p1_dead and not v["section"] else 32), v
        assert v["section"] == 1 or (p1_dead and v["players"][1]["x"] < 4500), (
            "P2 still trapped after native midboss retirement",
            v,
        )
        return dict(p1_dead=p1_dead, native_exit=v, views=v["views"])
    finally:
        r.release()
        sample("mushroom-final-probe", True)


def owl_cannon_origins(s):
    r = s.r
    rows = []
    beams = []
    directions = set()
    try:
        for section in (0, 1):
            if not section:
                s.load(7, section)
                r.fixture(5, 3)
                time.sleep(1)
                s.sample("owl-start-" + str(section), True)
            for x in [1310, 1450, 1630] if not section else [1139, 1301, 1506]:
                if section:
                    s.load(7, 1)
                    time.sleep(1)
                    r.wait_playable(45, advance_dialogue=True)
                    r.fixture(5, 3)
                    s.wait(
                        "owl-fresh-checkpoint",
                        lambda v: all(
                            p["state"] == 1
                            and p["hp"] == 32
                            and p["action"] == 2
                            and p["visible"]
                            for p in v["players"]
                        )
                        and v["players"][0]["x"] == 224
                        and v["players"][1]["x"] == 248,
                        30,
                    )
                # Match healthy recorded roots beneath the part2 low ceiling.
                y = 300 if not section else 938
                r.teleport(1, x, y)
                time.sleep(0.5)
                for n in range(32):
                    if n % 2 == 0:
                        r.teleport(1, x, y)
                    v = s.sample("owl-%d-%d-%d" % (section, x, n))
                    v["pools"] = _actor_pools(r)
                    data = r.read(0x80142F98, 32 * 0x30)
                    v["pools"]["stage"] = [
                        dict(
                            slot=i,
                            type=p[1],
                            subtype=p[2],
                            x=struct.unpack_from("<h", p, 10)[0],
                            y=struct.unpack_from("<h", p, 14)[0],
                            raw=p.hex(),
                        )
                        for i in range(32)
                        if (p := data[i * 0x30 : (i + 1) * 0x30])[0]
                    ]
                    rows.append(v)
                    parents = {
                        0x8013BED0 + p["slot"] * 0x9C: p for p in v["pools"]["enemy"]
                    }
                    for b in v["pools"]["secondary"]:
                        if b["type"] != 36:
                            continue
                        raw = bytes.fromhex(b["raw"])
                        p = parents.get(struct.unpack_from("<I", raw, 0x7C)[0])
                        if not p or abs(p["x"] - x) > 250:
                            continue
                        offset = (400 if b["subtype"] else 144) * (
                            1 if raw[0x15] else -1
                        )
                        observation = dict(
                            frame=v["frame"],
                            emitter=p["x"],
                            beam=b["x"],
                            offset=b["x"] - p["x"],
                            expected=offset,
                            facing=raw[0x15],
                            hero_x=x,
                        )
                        beams.append(observation)
                        # Exclude transient camera easing after development position setup.
                        if n > 10:
                            assert abs(b["x"] - p["x"] - offset) < 1, (
                                "Beam left its authored emitter",
                                observation,
                            )
                            directions.add(bool(raw[0x15]))
                    if n in (5, 20):
                        capture_pair(
                            r, s.output / ("owl-%d-%d-%d.png" % (section, x, n))
                        )
                    if any(not p["hp"] for p in v["players"]):
                        break
                    time.sleep(0.1)
                if any(not p["hp"] for p in rows[-1]["players"]):
                    break
        assert directions == {False, True}, (
            "Both cannon facings were not observed",
            directions,
        )
        return dict(
            survey=True,
            samples=len(rows),
            native_part2_beams=beams,
            facings=sorted(directions),
        )
    finally:
        r.release()
        (s.output / "owl-observations.json").write_text(json.dumps(rows, indent=2))
        (s.output / "owl-beams.json").write_text(json.dumps(beams, indent=2))
