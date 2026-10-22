"""Controlled native checks for opening effects, entry and P2 pause exits.

Fixtures prepare positions/checkpoints and protection. Original controller
input, shake commands, boss admission and frontend actions commit the results.
The corridor is walked from its original checkpoint through every slope area.
"""

import json
import struct
import threading
import time

from coop_debug import capture_pair
from coop_mushroom_followup_scenarios import intro_first_drop


def intro_effect_corridor(s):
    results = []
    output = s.output
    try:
        for owner in (1, 0):
            s.output = output / ("corridor-leader-%d" % owner)
            s.output.mkdir()
            results.append(_intro_effect_corridor(s, owner))
    finally:
        s.output = output
    return dict(native_corridors=results)


def _intro_effect_corridor(s, owner):
    r = s.r
    if getattr(s, "baseline_checkpoint_setup", False):
        s.load(0, 0)
        # Same data-only preparation as development fixture3, whose old
        # allowlist omitted the three audited Intro part1 spawn records.
        r.write(0x801721DD, 2)
        r.write(0x801721DE, 0)
        r.write(0x801721C0, 5)
        time.sleep(0.5)
        r.wait_playable(45, advance_dialogue=True)
    else:
        s.load(0, 0, 2)
    r.fixture(5, 3)
    s.wait(
        "corridor-arrived",
        lambda v: all(
            p["state"] == 1 and p["action"] == 2 and p["grounded"] for p in v["players"]
        ),
        15,
    )
    # Approach from the real checkpoint instead of skipping the slope.
    state = next(
        c["count"]
        for c in r.request("mod_counters")["counters"]
        if c["name"] == "mmx4.coop.split-state"
    )
    time.sleep(3)
    rows = []

    def sample(label, shot=False):
        v = s.sample(label)
        data = r.read(state + 16, 504)
        views = [data[n * 252 : (n + 1) * 252] for n in range(2)]
        v["raw_views"] = [p.hex() for p in views]
        v["raw_canonical"] = r.read(0x801419B0, 252).hex()
        v["raw_players"] = [p.hex() for p in r.players()]
        v["controllers"] = r.read(0x80142F98, 32 * 48).hex()
        v["views"] = [
            dict(
                x=struct.unpack_from("<h", p, 10)[0],
                y=struct.unpack_from("<h", p, 14)[0],
                flags=struct.unpack_from("<H", p, 0x34)[0],
                timers=list(p[0x36:0x38]),
                amplitude=list(p[0x45:0x47]),
                bounds=list(struct.unpack_from("<4h", p, 0x24)),
            )
            for p in views
        ]
        data = r.read(0x80142F98, 32 * 48)
        v["explosions"] = [
            dict(
                slot=i,
                phase=list(p[4:8]),
                x=struct.unpack_from("<h", p, 10)[0],
                y=struct.unpack_from("<h", p, 14)[0],
            )
            for i in range(32)
            if (p := data[i * 48 : (i + 1) * 48])[0] and p[1] == 28
        ]
        rows.append(v)
        if shot:
            capture_pair(r, s.output / (label + ".png"))
        return v

    sample("corridor-p2-leading-before", True)
    try:
        r.input(0xFFDF, owner)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            v = sample("corridor-p2-leading")
            assert all(p["hp"] == 32 for p in v["players"]), v
            if v["players"][owner]["x"] >= 4748:
                break
            time.sleep(0.06)
        else:
            raise AssertionError(("P2 did not reach corridor end", v))
        r.release()
        for i in range(40):
            sample("corridor-p2-effect-%02d" % i, i in (0, 20, 39))
            time.sleep(0.05)
        r.input(0xFFDF, owner ^ 1)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            v = sample("corridor-p1-catching-up")
            assert all(p["hp"] == 32 for p in v["players"]), v
            if v["players"][owner ^ 1]["x"] >= 4700:
                break
            time.sleep(0.06)
        else:
            raise AssertionError(("P1 did not reach corridor end", v))
        r.release()
        time.sleep(1)
        final = sample("corridor-both-nearby", True)
        counts = [
            sum(
                bool(v["flags"] & 1 and v["timers"][1] and v["amplitude"][1])
                for row in rows
                for v in [row["views"][seat]]
            )
            for seat in range(2)
        ]
        assert all(counts), ("Nearby views did not both receive corridor shake", counts)
        assert any(e["x"] > 4000 for row in rows for e in row["explosions"]), (
            "Explosions did not stay in corridor"
        )
        assert all(
            v["bounds"][2:] == [360, 360] and abs(v["y"] - 360) <= 4
            for v in final["views"]
        ), ("Cameras left their native slope limits/quake amplitude", final["views"])
        return dict(
            leader=owner, native_corridor=True, shake_samples=counts, final=final
        )
    finally:
        r.release()
        (s.output / "corridor-observations.json").write_text(json.dumps(rows, indent=2))
        (s.output / "corridor-counters.json").write_text(
            json.dumps(r.request("mod_counters"), indent=2)
        )


def intro_distant_entry(s):
    r = s.r
    r.fixture(5, 3)
    s.load(0, 1)
    r.fixture(5, 3)
    r.teleport(1, 3936, 442 if not s.campaign else 443)
    s.watch_enemy = 8
    state = next(
        c["count"]
        for c in r.request("mod_counters")["counters"]
        if c["name"] == "mmx4.coop.split-state"
    )
    deadline = time.monotonic() + 15
    while struct.unpack("<h", r.read(state + 16 + 252 + 10, 2))[0] < 3700:
        assert time.monotonic() < deadline, "P2 camera failed to settle before approach"
        time.sleep(0.1)

    def sample(label, shot=False):
        v = s.sample(label)
        views = [r.read(state + 16 + seat * 252, 252) for seat in range(2)]
        v["views"] = [
            dict(
                x=struct.unpack_from("<h", p, 10)[0],
                y=struct.unpack_from("<h", p, 14)[0],
                bounds=list(struct.unpack_from("<4h", p, 0x24)),
                shake=list(p[0x34:0x40]),
            )
            for p in views
        ]
        v["general"] = [
            dict(
                slot=i,
                kind=p[1],
                phase=list(p[4:8]),
                x=struct.unpack_from("<h", p, 10)[0],
                y=struct.unpack_from("<h", p, 14)[0],
            )
            for i in range(32)
            if (p := r.read(0x80142F98 + i * 48, 48))[0]
        ]
        if shot:
            capture_pair(r, s.output / (label + ".png"))
        return v

    before = sample("distant-p1-before-entry", True)
    print(json.dumps(dict(before=before)), flush=True)
    deadline = time.monotonic() + 25
    shots = 0
    try:
        while time.monotonic() < deadline:
            v = sample("distant-p1-entry")
            if any(g["kind"] == 24 for g in v["general"]) and shots == 0:
                sample("distant-p1-warning", True)
                shots += 1
            enemies = [
                e
                for e in s.enemies()
                if e["type"] == 8 and e["hp"] > 1 and e["state"][0]
            ]
            if (
                enemies
                and enemies[0]["state"][1] >= 3
                and not v["blocked"]
                and not any(g["kind"] == 24 for g in v["general"])
                and all(
                    p["active"]
                    and p["visible"]
                    and p["state"] == 1
                    and not p["script"]
                    and not p["door"]
                    for p in v["players"]
                )
            ):
                break
            if v["blocked"]:
                r.input(0xBFFF, 0)
                r.input(0xBFFF, 1)
                time.sleep(0.04)
                r.release()
            else:
                r.input(0xFFDF, 1)
            time.sleep(0.05)
        else:
            final = sample("distant-p1-stall", True)
            (s.output / "entry-stall.json").write_text(json.dumps(final, indent=2))
            (s.output / "entry-counters.json").write_text(
                json.dumps(r.request("mod_counters"), indent=2)
            )
            raise AssertionError(
                "P2-led boss entry did not release with distant living P1"
            )
    finally:
        r.release()
    s.wait(
        "distant-p1-controls-released",
        lambda v: all(p["action"] == 2 and p["hp"] > 0 for p in v["players"]),
        8,
    )
    after = sample("distant-p1-fight", True)
    x = after["players"][1]["x"]
    r.input(0xFFDF, 1)
    time.sleep(0.4)
    r.release()
    controls = sample("distant-p1-controls", True)
    assert controls["players"][1]["x"] > x + 5, ("P2 controls not restored", controls)
    return dict(before=before, after=after, controls=controls, native_p2_led_intro=True)


def intro_structure_shake(s):
    r = s.r
    rows = []
    done = threading.Event()
    state = next(
        c["count"]
        for c in r.request("mod_counters")["counters"]
        if c["name"] == "mmx4.coop.split-state"
    )

    def observe():
        while not done.is_set():
            views = [r.read(state + 16 + seat * 252, 252) for seat in range(2)]
            rows.append(
                [
                    dict(
                        x=struct.unpack_from("<h", p, 10)[0],
                        y=struct.unpack_from("<h", p, 14)[0],
                        flags=struct.unpack_from("<H", p, 0x34)[0],
                        timers=list(p[0x36:0x38]),
                        amplitude=list(p[0x45:0x47]),
                    )
                    for p in views
                ]
            )
            time.sleep(0.012)

    worker = threading.Thread(target=observe)
    worker.start()
    try:
        result = intro_first_drop(s)
        time.sleep(0.7)
        capture_pair(r, s.output / "first-drop-presentation.png")
    finally:
        done.set()
        worker.join(5)
        (s.output / "native-shake-samples.json").write_text(json.dumps(rows, indent=2))

    def active(v):
        return ((v["flags"] & 16) and v["timers"][0] and v["amplitude"][0]) or (
            (v["flags"] & 1) and v["timers"][1] and v["amplitude"][1]
        )

    counts = [sum(bool(active(v[seat])) for v in rows) for seat in range(2)]
    (s.output / "shake-result.json").write_text(
        json.dumps(dict(samples=len(rows), shake_samples=counts), indent=2)
    )
    assert counts[1] > 0, ("P2 saw no native falling-object shake", counts)
    return dict(**result, samples=len(rows), shake_samples=counts)


def intro_closing_shake(s):
    r = s.r
    # Select the original late checkpoint before waiting for its playable
    # state. The separate section1 checkpoint0 arrival script is not part
    # of this wall check and can still have P2 in its entry pose.
    r.fixture(1, 0, 1, s.campaign)
    s.wait(
        "closing-section-allocated",
        lambda v: v["mode"][0] == 6 and v["stage"] == 0 and v["section"] == 1,
        30,
    )
    time.sleep(0.5)
    s.wait(
        "closing-coop-enrolled",
        lambda v: bool(struct.unpack("<I", r.read(r.diagnostic() + 8, 4))[0]),
        30,
    )
    r.fixture(3, 1)
    r.wait_playable(30, advance_dialogue=True)
    r.fixture(5, 3)
    s.wait(
        "closing-checkpoint-arrival",
        lambda v: all(
            p["state"] == 1 and p["action"] == 2 and p["hp"] == 32 for p in v["players"]
        ),
        20,
    )
    # Prepare the observed solid platform, then let native camera streaming
    # catch up before approaching the wall/shaft. A direct shaft teleport
    # drops below the view before its camera areas have been loaded.
    r.teleport(1, 3280, 443)
    state = next(
        c["count"]
        for c in r.request("mod_counters")["counters"]
        if c["name"] == "mmx4.coop.split-state"
    )
    deadline = time.monotonic() + 15
    while struct.unpack("<h", r.read(state + 16 + 252 + 10, 2))[0] < 3000:
        if time.monotonic() >= deadline:
            raise TimeoutError("Closing approach camera did not settle")
        time.sleep(0.05)
    # Start on the recorded upper platform before the shaft. Directly entering
    # below the native camera-area boundary skips its admission and is lethal.
    # Original movement must cross that boundary and trigger the actual walls.
    r.teleport(1, 3509, 362)
    rows = []
    seen = [0, 0]
    closed_wall = False
    wall_axes = [0, 0]
    closing_seen = False
    retreated = False
    hover_y = 854
    hover_at = 0
    descended = False
    deadline = time.monotonic() + 30
    try:
        r.input(0xFFDF, 1)
        while time.monotonic() < deadline:
            row = s.sample("closing-p2-descending")
            data = r.read(state + 16, 504)
            pool = r.read(0x80165A30, 32 * 0x8C)
            row["walls"] = [
                dict(
                    slot=i,
                    phase=list(p[4:8]),
                    x=struct.unpack_from("<h", p, 10)[0],
                    y=struct.unpack_from("<h", p, 14)[0],
                )
                for i in range(32)
                if (p := pool[i * 0x8C : (i + 1) * 0x8C])[0] and p[1] == 3
            ]
            closing = any(w["phase"][0] == 2 for w in row["walls"])
            closing_seen |= closing
            # Native phase3 retires each piece in the same update as the
            # final vertical command; the actor is absent when sampled.
            closed_wall |= closing_seen and not row["walls"]
            row["views"] = [
                dict(
                    x=struct.unpack_from("<h", data, n * 252 + 10)[0],
                    y=struct.unpack_from("<h", data, n * 252 + 14)[0],
                    enabled=data[n * 252 + 0x44],
                    bounds=list(struct.unpack_from("<4h", data, n * 252 + 0x24)),
                    flags=struct.unpack_from("<H", data, n * 252 + 0x34)[0],
                    timers=list(data[n * 252 + 0x36 : n * 252 + 0x38]),
                    amplitudes=list(data[n * 252 + 0x45 : n * 252 + 0x47]),
                )
                for n in range(2)
            ]
            rows.append(row)
            for axis, bit in enumerate([16, 1]):
                v = row["views"][1]
                if v["flags"] & bit and v["timers"][axis] and v["amplitudes"][axis]:
                    seen[axis] += 1
                    if (closing if axis == 0 else closed_wall) and v["amplitudes"][
                        axis
                    ] == (2 if axis else 3):
                        wall_axes[axis] += 1
            assert all(p["hp"] == 32 for p in row["players"]), (
                "Closing fixture changed health",
                row,
            )
            descended |= row["players"][1]["y"] >= 940
            if descended and all(wall_axes) and closed_wall:
                break
            if descended and wall_axes[0] and not retreated:
                capture_pair(r, s.output / "closing-bottom-p2-shake.png")
                # Position-only protection isolates shake from crush survival.
                # Ascend in view-sized steps so native camera easing can follow;
                # a direct teleport above the active camera is lethal.
                r.release()
                r.teleport(1, 3744, hover_y)
                hover_at = time.monotonic() + 0.15
                retreated = True
            if retreated and time.monotonic() >= hover_at:
                hover_y = max(320, hover_y - 100)
                r.teleport(1, 3744, hover_y)
                hover_at = time.monotonic() + 0.15
            if not retreated:
                r.input(0xFFDF if row["players"][1]["x"] < 3770 else 0xFFFF, 1)
            time.sleep(0.02)
        else:
            raise AssertionError(
                (
                    "Closing wall did not finish with both native shake axes",
                    seen,
                    wall_axes,
                    closed_wall,
                    row,
                )
            )
        capture_pair(r, s.output / "closing-native-p2-shake.png")
        return dict(
            native_closing_shake=seen,
            wall_shake=wall_axes,
            closed_wall=closed_wall,
            native_descent=descended,
            retreated_for_effect_isolation=retreated,
            final=row,
        )
    finally:
        r.release()
        (s.output / "closing-observations.json").write_text(json.dumps(rows, indent=2))


def p2_pause_quit(s):
    r = s.r
    s.load(1, 0)
    r.fixture(5, 3)
    r.fixture(2, 0, 0x80)
    s.wait(
        "quit-p1-dead",
        lambda v: v["players"][0]["state"] == 3 and v["players"][0]["hp"] == 0,
        15,
    )
    before = s.sample("quit-survivor-before")
    campaign = before["campaign"]
    clears = r.read(0x80172219, 1)[0]

    def pulse(buttons, seat=1):
        r.input(buttons, seat)
        time.sleep(0.16)
        r.release()
        time.sleep(0.18)

    def opened():
        pulse(0xFFF7)
        s.wait(
            "quit-survivor-pause", lambda v: v["menu"][0] == 1 and v["menu"][1] < 3, 10
        )

    opened()
    pulse(0xFFFE)
    s.wait("quit-survivor-p2-popup", lambda v: v["menu"] == [1, 6], 10)
    time.sleep(0.9)
    capture_pair(r, s.output / "p2-quit-with-p1-dead.png")
    pulse(0xBFFF, 0)
    assert r.read(0x801754A5, 1)[0] == 6, "Dead P1 confirmed P2 popup"
    pulse(0xBFFF)
    s.wait(
        "quit-survivor-cancelled", lambda v: v["menu"][0] == 1 and v["menu"][1] < 3, 10
    )
    pulse(0xFFF7)
    s.wait("quit-survivor-resumed", lambda v: v["mode"][:2] == [6, 0], 10)
    x = s.sample("quit-cancel-before-movement")["players"][1]["x"]
    r.input(0xFFDF, 1)
    time.sleep(0.4)
    r.release()
    assert s.sample("quit-cancel-after-movement")["players"][1]["x"] > x + 5
    opened()
    pulse(0xFFFE)
    s.wait("quit-survivor-reopened", lambda v: v["menu"] == [1, 6], 10)
    time.sleep(0.9)
    pulse(0xFFBF)
    pulse(0xBFFF)
    time.sleep(0.5)
    capture_pair(r, s.output / "p2-quit-second-confirmation.png")
    pulse(0xFFBF)
    pulse(0xBFFF)
    deadline = time.monotonic() + 18
    while time.monotonic() < deadline:
        front = r.read(0x80173C70, 0x20)
        if front[:2] == bytes([6, 1]):
            break
        if front[0] < 6:
            pulse(0xFFF7, 0)
        else:
            time.sleep(0.06)
    else:
        raise AssertionError(
            ("P2 confirmed Quit did not reach title", s.sample("quit-stuck"))
        )
    after = s.sample("p2-quit-title")
    capture_pair(r, s.output / "p2-quit-returned-title.png")
    cache = list(r.read(0x800F1D90, 8))
    assert cache[0] == campaign and cache[4] == clears, cache
    return dict(
        p2_quit_confirmed=True,
        p1_dead=True,
        p2_cancel_resume_and_controls=True,
        campaign=campaign,
        clears=clears,
        before=before,
        after=after,
    )


def p2_pause_escape(s):
    r = s.r
    s.load(5, 1, 1)
    r.fixture(5, 3)
    r.write(0x80172219, 16)
    r.write(0x80141981, 16)
    r.fixture(2, 0, 0x80)
    s.wait(
        "escape-p1-dead",
        lambda v: v["players"][0]["state"] == 3 and v["players"][0]["hp"] == 0,
        15,
    )
    before = s.sample("escape-before")
    clears = r.read(0x80172219, 1)[0]

    def pulse(buttons, seat=1):
        r.input(buttons, seat)
        time.sleep(0.15)
        r.release()
        time.sleep(0.18)

    pulse(0xFFF7)
    s.wait("escape-p2-pause", lambda v: v["menu"][0] == 1 and v["menu"][1] < 3, 12)
    time.sleep(0.6)
    capture_pair(r, s.output / "p2-escape-menu.png")
    assert r.read(0x801754C3, 1)[0], "Native Escape eligibility was not prepared"
    if s.campaign:  # X/P2: follow weapon grid down to the bottom row.
        for _ in range(5):
            pulse(0xFFBF)
    for choice in range(8):
        capture_pair(r, s.output / "p2-escape-selected.png")
        pulse(0xBFFF)
        if r.read(0x801754D0, 4) != bytes(4) or r.read(0x801721C0, 2) != bytes([6, 2]):
            break
        pulse(0xFFDF)
    else:
        raise AssertionError("Native P2 Escape was never selectable")
    deadline = time.monotonic() + 65
    while time.monotonic() < deadline:
        v = s.sample("p2-native-escape")
        if v["mode"][:2] == [3, 4]:
            break
        # Confirm native save UI/dialogue. Use the movie's Start skip in
        # mode3/8; Cross carried through its finish can immediately select
        # a new stage after Escape has correctly returned to the board.
        if v["mode"][0] in (12, 9) or v["mode"][:2] == [3, 9]:
            pulse(0xBFFF, 0)
        elif v["mode"][:2] == [3, 8]:
            pulse(0xFFF7, 0)
        else:
            time.sleep(0.05)
    else:
        capture_pair(r, s.output / "escape-board-stall.png")
        raise AssertionError(("P2 Escape did not return to stage board", v))
    capture_pair(r, s.output / "p2-escape-returned-board.png")
    assert r.read(0x80172219, 1)[0] == clears, "Escape changed campaign clears"
    return dict(
        native_p2_escape=True, p1_dead=True, clears=clears, before=before, after=v
    )
