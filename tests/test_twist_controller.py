import pytest
import asyncio
from pyflichub.twist_controller import RateDetentController, clamp, sign


def test_clamp():
    assert clamp(5, 0, 10) == 5
    assert clamp(-1, 0, 10) == 0
    assert clamp(11, 0, 10) == 10
    assert clamp(0, 0, 10) == 0
    assert clamp(10, 0, 10) == 10


def test_sign():
    assert sign(5) == 1
    assert sign(-5) == -1
    assert sign(0) == 0


@pytest.mark.asyncio
async def test_controller_basic():
    ctrl = RateDetentController({"tickMs": 100})  # Make tick fast for less waiting if tested

    # Initialize with center
    res1 = ctrl.update_raw(50)
    assert res1["dir"] == 0
    assert res1["speed"] == 0
    assert res1["intentChanged"] is True

    # Move slightly, within deadband
    res2 = ctrl.update_raw(52)
    assert res2["dir"] == 0
    assert res2["speed"] == 0

    # Move outside deadband
    res3 = ctrl.update_raw(60)
    assert res3["dir"] == 1
    assert res3["speed"] == 1
    assert res3["intentChanged"] is True

    assert ctrl.get_actual_out_pct() == 0 # Default minOutPct


@pytest.mark.asyncio
async def test_controller_tick():
    values = []

    def on_change(val):
        values.append(val)

    # Initializing at outPct = 50
    ctrl = RateDetentController({
        "tickMs": 50,
        "initialOutPct": 50,
        "minOutPct": 0,
        "maxOutPct": 100,
        "deadbandEnter": 5,
        "deadbandExit": 9
    }, on_change_callback=on_change)

    # set center
    ctrl.update_raw(50)

    # move outside deadband (50 + 10 = 60), diff is 10, speed should be 1, dir = 1
    ctrl.update_raw(60)

    # wait for some ticks
    await asyncio.sleep(0.16)

    ctrl.stop()

    assert len(values) > 0
    assert ctrl.get_actual_out_pct() > 50
    assert values[-1] == ctrl.get_actual_out_pct()
