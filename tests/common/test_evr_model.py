#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Known-vector unit tests of the EVR V2 trigger model.

Test methodology:
    Sweep: the trigger and channel configuration layouts, bit_size and
        queue_capacity at the depths the simulations use (0, 1, 4, 16, 28 and
        127), and TriggerModel traces for delays 0 to 50 and widths 1 to 5,
        polarity 0 and 1, fire spacings of 1 to 3 cycles, a reduced delay, a
        width of 0, and a clear by enabled or rst.
    Stimulus: TriggerModel.step is called directly, three reset cycles first,
        with the same inputs the cocotb tests apply to the RTL.
    Checks: pack and unpack round trip and place every field at its toSlv
        offset; the model traces equal the vectors listed here. The vectors
        were captured from the production EvrV2Trigger under GHDL by
        tests/lcls2_evr/test_EvrV2Trigger.py, so they are regression pins of
        the shipped RTL, not independent evidence of intended behavior.
    Timing: none, no simulator.
    Propagation sampling: not applicable, no simulator is involved.
"""

import pytest

from tests.common import evr_model, timing_model

RESET_CYCLES = 3
DEPTHS = [0, 1, 4, 16, 28, 127]


def fields(**values):
    return {**evr_model.TRIGGER_CONFIG_DEFAULTS, **values}


def run_model(length, config, fires=(), arm_from=3, depth=16, clears=(), resets=(), channels=1, use_mask=False, arm=1):
    """Step a TriggerModel and return the level seen during each cycle (element 0 is power-up)."""
    model = evr_model.TriggerModel(trig_depth=depth, channels=channels, use_mask=use_mask)
    trace = [0]
    for cycle in range(length):
        rst = 1 if cycle < RESET_CYCLES or cycle in resets else 0
        base = config(cycle) if callable(config) else config
        values = {**base, "enabled": 0} if cycle in clears else base
        trace.append(model.step(values, arm if cycle >= arm_from else 0, 1 if cycle in fires else 0, rst))
    return trace


def edges(trace):
    rises = [k for k in range(1, len(trace)) if trace[k - 1] == 0 and trace[k] == 1]
    falls = [k for k in range(1, len(trace)) if trace[k - 1] == 1 and trace[k] == 0]
    return rises, falls


def test_trigger_config_layout():
    offsets = {"enabled": 0, "polarity": 1, "complEn": 2, "complAnd": 3, "delay": 4, "width": 32,
               "channel": 60, "channels": 64, "delayTap": 80, "loadTap": 86}
    widths = {name: width for name, width, _ in evr_model.TRIGGER_CONFIG_FIELDS}
    zero = {name: 0 for name in offsets}
    for name, offset in offsets.items():
        ones = (1 << widths[name]) - 1
        word = evr_model.pack_trigger_config(**{**zero, name: ones})
        assert word == ones << offset, name
        assert evr_model.unpack_trigger_config(word) == {**zero, name: ones}, name
    assert evr_model.TRIGGER_CONFIG_BITS == 87
    assert sum(w * c for _, w, c in evr_model.TRIGGER_CONFIG_FIELDS) == 87


def test_trigger_config_known_words():
    assert evr_model.pack_trigger_config(enabled=1, polarity=1, delay=3, width=2) == 1 | 2 | (3 << 4) | (2 << 32)
    assert evr_model.pack_trigger_config() == 2 | (1 << 32)
    word = evr_model.pack_trigger_config(enabled=1, polarity=0, complEn=1, complAnd=1, delay=0x123, width=0x45,
                                         channel=9, channels=0xA5A5, delayTap=0x2A, loadTap=1)
    assert word == 1 | (1 << 2) | (1 << 3) | (0x123 << 4) | (0x45 << 32) | (9 << 60) | (0xA5A5 << 64) | (0x2A << 80) | (1 << 86)
    assert evr_model.unpack_trigger_config(word) == {
        "enabled": 1, "polarity": 0, "complEn": 1, "complAnd": 1, "delay": 0x123, "width": 0x45,
        "channel": 9, "channels": 0xA5A5, "delayTap": 0x2A, "loadTap": 1,
    }


def test_channel_config_layout():
    assert evr_model.CHANNEL_CONFIG_BITS == 81
    assert sum(w * c for _, w, c in evr_model.CHANNEL_CONFIG_FIELDS) == 81
    word = evr_model.pack_channel_config(enabled=1, rateSel=0x1FFF, destSel=0x7FFFF, bsaEnabled=1, bsaActiveSetup=0x3F,
                                         bsaActiveDelay=0xFFFFF, bsaActiveWidth=0xFFFFF, dmaEnabled=1)
    assert word == (1 << 81) - 1
    assert evr_model.pack_channel_config() == 1 << 60
    assert evr_model.pack_channel_config(enabled=1, rateSel=5, destSel=7, bsaActiveSetup=3) == (
        1 | (5 << 1) | (7 << 14) | (3 << 34) | (1 << 60)
    )
    assert evr_model.unpack_channel_config(1 << 60)["bsaActiveWidth"] == 1


def test_pack_rejects_bad_fields():
    with pytest.raises(ValueError):
        evr_model.pack_trigger_config(unknown=1)
    with pytest.raises(ValueError):
        evr_model.pack_trigger_config(channel=16)
    with pytest.raises(ValueError):
        evr_model.pack_channel_config(rateSel=1 << 13)


def test_bit_size_table():
    table = {0: 1, 1: 1, 2: 2, 3: 2, 4: 3, 15: 4, 16: 5, 28: 5, 127: 7, 128: 8}
    for value, bits in table.items():
        assert evr_model.bit_size(value) == bits, value
    with pytest.raises(ValueError):
        evr_model.bit_size(-1)


def test_queue_capacity_table():
    table = {0: 3, 1: 3, 4: 9, 16: 33, 28: 33, 127: 129}
    for depth, pulses in table.items():
        assert evr_model.queue_capacity(depth) == pulses, depth


def test_single_pulse_trace():
    config = fields(enabled=1, polarity=1, delay=3, width=2, channel=0)
    trace = run_model(103, config, fires=(12,), arm_from=10)
    assert edges(trace) == ([19], [21])
    assert [k for k, level in enumerate(trace) if level] == [19, 20]


@pytest.mark.parametrize("delay", [0, 1, 2, 3, 10, 50])
@pytest.mark.parametrize("width", [1, 2, 5])
def test_latency_table(delay, width):
    config = fields(enabled=1, polarity=1, delay=delay, width=width)
    trace = run_model(delay + width + 43, config, fires=(12,), arm_from=8)
    rise = 12 + evr_model.FIRE_TO_RISE_CYCLES + delay
    assert edges(trace) == ([rise], [rise + width])


def test_fire_spacing():
    config = fields(enabled=1, polarity=1, delay=3, width=1)
    assert edges(run_model(73, config, fires=(20, 22, 24)))[0] == [27, 31]
    assert edges(run_model(73, config, fires=(20, 23, 26)))[0] == [27, 30, 33]
    assert edges(run_model(73, config, fires=(20, 21, 22, 23)))[0] == [27, 30]
    assert evr_model.MIN_FIRE_SPACING == 3


def test_pulses_in_flight_follow_queue_capacity():
    config = fields(enabled=1, polarity=1, delay=40, width=2)
    fires = (20, 30, 40, 50)
    for depth in DEPTHS:
        rises, falls = edges(run_model(123, config, fires=fires, depth=depth))
        accepted = min(len(fires), evr_model.queue_capacity(depth))
        assert rises == [f + 44 for f in fires[:accepted]], depth
        want_falls = [f + 46 for f in fires[:accepted]]
        assert falls == (want_falls[:-1] if accepted < len(fires) else want_falls), depth


def test_overflow_drops_later_fires_and_leaves_output_high():
    config = fields(enabled=1, polarity=1, delay=1000, width=1)
    fires = tuple(20 + 4 * k for k in range(140))
    for depth in DEPTHS:
        trace = run_model(1700, config, fires=fires, depth=depth)
        rises, falls = edges(trace)
        capacity = evr_model.queue_capacity(depth)
        assert len(rises) == capacity, depth
        assert len(falls) == capacity - 1, depth
        assert trace[-1] == 1, depth


def test_skip_rules():
    base = dict(enabled=1, polarity=1, delay=50, width=1)

    def reduced(cycle):
        return fields(**base) if cycle < 24 else fields(enabled=1, polarity=1, delay=5, width=1)

    assert edges(run_model(123, reduced, fires=(20, 28)))[0] == [74]
    assert edges(run_model(163, reduced, fires=(20, 100)))[0] == [74, 109]
    assert not any(run_model(83, fields(enabled=1, polarity=1, delay=3, width=0), fires=(20, 40)))


@pytest.mark.parametrize("how", ["enabled", "rst"])
def test_clear_drops_queued_pulses(how):
    config = fields(enabled=1, polarity=1, delay=60, width=3)
    clears = (30,) if how == "enabled" else ()
    resets = (30,) if how == "rst" else ()
    assert not any(run_model(143, config, fires=(20,), clears=clears, resets=resets))

    config = fields(enabled=1, polarity=1, delay=2, width=30)
    clears = (32,) if how == "enabled" else ()
    resets = (32,) if how == "rst" else ()
    trace = run_model(103, config, fires=(20,), clears=clears, resets=resets)
    assert edges(trace) == ([26], [33])


def test_polarity_traces():
    fires = (20, 60, 100)
    high = run_model(143, fields(enabled=1, polarity=1, delay=3, width=2), fires=fires)
    assert edges(high) == ([27, 67, 107], [29, 69, 109])
    low = run_model(143, fields(enabled=1, polarity=0, delay=3, width=2), fires=fires)
    assert edges(low) == ([29, 69, 109], [67, 107])
    assert not any(low[:29])


def test_mask_mode_ignores_channel_field():
    config = fields(enabled=1, polarity=1, delay=3, width=2, channel=0, channels=0b0110)
    for arm, fires in ((0b0001, False), (0b1000, False), (0b0010, True), (0b0100, True), (0b1010, True)):
        trace = run_model(63, config, fires=(20,), channels=4, use_mask=True, arm=arm)
        assert bool(edges(trace)[0]) == fires, bin(arm)


def test_channel_beyond_channel_count_is_rejected():
    model = evr_model.TriggerModel(channels=1)
    with pytest.raises(ValueError):
        for _ in range(8):
            model.step(fields(enabled=1, channel=1), 0, 0)


def test_model_starts_from_reset_state():
    model = evr_model.TriggerModel()
    assert model.step(fields(enabled=0), 0, 0) == 0
    model.reset()
    assert model.r["push_state"] == "DISABLED"


def test_trigger_compl_pass_through():
    for trig_in in range(4):
        for and_bits in ((0, 0), (0, 1), (1, 0), (1, 1)):
            assert evr_model.trigger_compl((0, 0), and_bits, trig_in) == trig_in


def test_trigger_compl_or_and_and():
    # Vector index t is trigIn: 1 is trigIn(0) only, 2 is trigIn(1) only, 3 is both.
    # One output complemented at a time; the other passes its own trigIn bit.
    assert [evr_model.trigger_compl((1, 0), (0, 0), t) for t in range(4)] == [0b00, 0b01, 0b11, 0b11]
    assert [evr_model.trigger_compl((1, 0), (1, 0), t) for t in range(4)] == [0b00, 0b00, 0b10, 0b11]
    assert [evr_model.trigger_compl((0, 1), (0, 0), t) for t in range(4)] == [0b00, 0b11, 0b10, 0b11]
    assert [evr_model.trigger_compl((0, 1), (0, 1), t) for t in range(4)] == [0b00, 0b01, 0b00, 0b11]
    # Both complemented: each output uses its own complAnd bit.
    assert [evr_model.trigger_compl((1, 1), (0, 0), t) for t in range(4)] == [0b00, 0b11, 0b11, 0b11]
    assert [evr_model.trigger_compl((1, 1), (1, 1), t) for t in range(4)] == [0b00, 0b00, 0b00, 0b11]
    assert [evr_model.trigger_compl((1, 1), (1, 0), t) for t in range(4)] == [0b00, 0b10, 0b10, 0b11]
    assert [evr_model.trigger_compl((1, 1), (0, 1), t) for t in range(4)] == [0b00, 0b01, 0b01, 0b11]


def test_trigger_compl_rejects_bad_input():
    with pytest.raises(ValueError):
        evr_model.trigger_compl((0, 0), (0, 0), 4)
    with pytest.raises(ValueError):
        evr_model.trigger_compl((2, 0), (0, 0), 0)


def select_config(**values):
    return {**evr_model.CHANNEL_CONFIG_DEFAULTS, **values}


def select_message(**values):
    return {**timing_model.default_message(), **values}


def test_rate_select_fixed_mode():
    msg = select_message(fixedRates=0b0000000101)
    levels = [evr_model.rate_select(select_config(rateSel=index), msg, 0) for index in range(16)]
    assert levels == [1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    top = select_message(fixedRates=0b1000000000)
    assert evr_model.rate_select(select_config(rateSel=9), top, 0) == 1
    assert evr_model.rate_select(select_config(rateSel=10), select_message(fixedRates=0x3FF), 0) == 0


def test_rate_select_ac_mode():
    msg = select_message(acRates=0b100101, acTimeSlot=3)
    mask_bit = 1 << (3 + 2)
    levels = [evr_model.rate_select(select_config(rateSel=(1 << 11) | mask_bit | index), msg, 0) for index in range(8)]
    assert levels == [1, 0, 1, 0, 0, 1, 0, 0]
    assert evr_model.rate_select(select_config(rateSel=(1 << 11) | 0), msg, 0) == 0
    other_slot = select_message(acRates=0b111111, acTimeSlot=2)
    assert evr_model.rate_select(select_config(rateSel=(1 << 11) | mask_bit), other_slot, 0) == 0
    assert evr_model.rate_select(select_config(rateSel=(1 << 11) | (1 << 4)), other_slot, 0) == 1


def test_rate_select_ac_mode_edge_slots():
    # Slots 0 and 7 read mask bits 2 and 9: observed, intent unconfirmed.
    msg0 = select_message(acRates=0b111111, acTimeSlot=0)
    assert evr_model.rate_select(select_config(rateSel=(1 << 11) | (1 << 2)), msg0, 0) == 1
    msg7 = select_message(acRates=0b111111, acTimeSlot=7)
    assert evr_model.rate_select(select_config(rateSel=(1 << 11) | (1 << 9)), msg7, 0) == 1
    assert evr_model.rate_select(select_config(rateSel=(1 << 11) | (1 << 8)), msg7, 0) == 0


def test_rate_select_control_and_reserved_modes():
    for bit in range(16):
        word = 1 << bit
        assert evr_model.rate_select(select_config(rateSel=(2 << 11) | bit), select_message(), word) == 1
        assert evr_model.rate_select(select_config(rateSel=(2 << 11) | ((bit + 1) % 16)), select_message(), word) == 0
    full = select_message(fixedRates=0x3FF, acRates=0x3F)
    assert evr_model.rate_select(select_config(rateSel=(3 << 11)), full, 0xFFFF) == 0


def test_dest_select_modes():
    mask = 1 << 5
    for beam_request, want in ((0x51, 1), (0x41, 0), (0x50, 0), (0x40, 0)):
        msg = select_message(beamRequest=beam_request)
        assert evr_model.dest_select(select_config(destSel=(0 << 16) | mask), msg) == want
    for beam_request, want in ((0x51, 0), (0x41, 1), (0x50, 1), (0x40, 1)):
        msg = select_message(beamRequest=beam_request)
        assert evr_model.dest_select(select_config(destSel=(1 << 16) | mask), msg) == want
    for beam_request in (0x51, 0x41, 0x00):
        msg = select_message(beamRequest=beam_request)
        assert evr_model.dest_select(select_config(destSel=2 << 16), msg) == 1
        assert evr_model.dest_select(select_config(destSel=(3 << 16) | 0xFFFF), msg) == 0


def test_dest_select_top_mask_bit_and_bit_18():
    msg = select_message(beamRequest=0xF1)
    assert evr_model.dest_select(select_config(destSel=1 << 15), msg) == 1
    assert evr_model.dest_select(select_config(destSel=(1 << 18) | (1 << 15)), msg) == 1
    assert evr_model.dest_select(select_config(destSel=(1 << 18) | (2 << 16)), msg) == 1
    assert evr_model.dest_select(select_config(destSel=(1 << 18)), select_message()) == 0


def test_event_select_model_registers_outputs_and_control_word():
    model = evr_model.EventSelectModel()
    config = select_config(enabled=1, dmaEnabled=1, rateSel=(2 << 11) | (3 << 4) | 5, destSel=2 << 16)
    control = [0] * 18
    control[3] = 1 << 5
    msg = select_message(control=control)
    # The control word is registered a clock behind: the first strobe sees the old word.
    assert model.step(config, 1, msg) == (0, 0)
    assert model.step(config, 1, msg) == (1, 1)
    assert model.step(config, 0, msg) == (0, 0)
    assert model.step({**config, "dmaEnabled": 0}, 1, msg) == (1, 0)
    assert model.step({**config, "enabled": 0}, 1, msg) == (0, 0)
    model.reset()
    assert model.control_word == 0


def test_event_select_model_refuses_control_index_overflow():
    model = evr_model.EventSelectModel()
    for index in (18, 31):
        with pytest.raises(ValueError, match="out of bounds"):
            model.step(select_config(enabled=1, rateSel=index << 4), 1, select_message())
    model.step(select_config(enabled=1, rateSel=17 << 4), 1, select_message())


def v1_stream(pulse_id=0, event_codes=0, **dbuff):
    values = {"dtype": 0, "version": 0, "dmod": 0, "epicsTime": 0, "edefAvgDn": 0, "edefMinor": 0, "edefMajor": 0,
              "edefInit": 0}
    values.update(dbuff)
    return {"pulseId": pulse_id, "eventCodes": event_codes, "dbuff": values}


def test_from_v1_time_fields():
    out = evr_model.from_v1(v1_stream(pulse_id=0x12345, epicsTime=0x0123456789ABCDEF), timing_model.default_message())
    assert out["pulseId"] == (0x12345 << 47) | (0x44D5 << 32) | 0x01234567
    assert out["timeStamp"] == 0x89ABCDEF01234567
    # Only the low 17 bits of the LCLS-I pulse id are kept.
    wide = evr_model.from_v1(v1_stream(pulse_id=0xFFFE0000), timing_model.default_message())
    assert wide["pulseId"] == 0


def test_from_v1_event_codes_and_modifier_words():
    codes = (0xABCD << 0) | (0x1234 << 16) | (0xFFFF << (16 * 15))
    dmod = 0
    for word, value in enumerate((0x1111, 0x2222, 0x3333, 0x4444, 0x5555, 0x6666, 0x7777, 0x8888)):
        dmod |= value << (16 * word)
    out = evr_model.from_v1(v1_stream(event_codes=codes, dmod=dmod), timing_model.default_message())
    assert out["control"][0] == 0xABCD and out["control"][1] == 0x1234 and out["control"][15] == 0xFFFF
    assert out["control"][2] == 0 and out["control"][17] == 0
    assert out["control"][16] == 0x7777
    assert out["beamEnergy"] == [0x1111, 0x2222, 0x3333, 0x4444]
    assert out["photonWavelen"] == [0x5555, 0x6666]
    assert out["mpsLimit"] == 0x8888


def test_from_v1_mps_class_and_ac_fields():
    # mpsClass(5) to mpsClass(7) share dmod(163:148) with the acRates bits, so the two are checked apart.
    dmod = 0
    for i in range(16):
        dmod |= (i & 0xF) << (128 + 4 * i)
    out = evr_model.from_v1(v1_stream(dmod=dmod), timing_model.default_message())
    assert out["mpsClass"] == list(range(16))
    # dmod(152:148) is the low bit of mpsClass(6) (0) above mpsClass(5) (0101): 00101, then acRates(0) = 1.
    assert out["acRates"] == 0b001011
    ac = evr_model.from_v1(v1_stream(dmod=(0b101 << 125) | (0b10110 << 148)), timing_model.default_message())
    assert ac["acTimeSlot"] == 0b101
    assert ac["acRates"] == 0b101101
    assert ac["fixedRates"] == 0


def test_from_v1_bsa_fields():
    with_init = evr_model.from_v1(
        v1_stream(edefInit=0x0000FFFF, edefMinor=0x12345678, edefMajor=0x9ABCDEF0, edefAvgDn=0x0F0F0F0F,
                  dmod=0xFFFFF << 128),
        timing_model.default_message(),
    )
    assert with_init["bsaInit"] == 0x0000FFFF
    assert with_init["bsaActive"] == 0x00005678 | 0xF0000
    assert with_init["bsaAvgDone"] == 0x0000DEF0 | 0x0F0F0000
    assert with_init["bsaDone"] == 0x0F0F0F0F


def test_from_v1_destination_rule():
    base = timing_model.default_message()
    for dmod, want in ((0, 2), (1 << 61, 0), (1 << 60, 1), ((1 << 61) | (1 << 60), 1)):
        assert evr_model.from_v1(v1_stream(dmod=dmod), base)["beamRequest"] == want << 4
    assert evr_model.from_v1(v1_stream(dmod=1 << 83), base)["beamRequest"] == (2 << 4) | 1


def test_from_v1_keeps_unassigned_fields():
    previous = {**timing_model.default_message(), "version": 7, "resync": 1, "syncStatus": 1, "mpsValid": 1, "bcsFault": 1}
    out = evr_model.from_v1(v1_stream(), previous)
    for name in ("version", "resync", "syncStatus", "mpsValid", "bcsFault"):
        assert out[name] == previous[name]
    assert previous["version"] == 7 and out is not previous
