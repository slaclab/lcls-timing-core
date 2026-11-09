#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

"""Reference model of the LCLS-II EVR trigger path.

Sources searched for an independent description of EVR V2 behavior: the
slaclab/lcls-timing-core repository page, the SLAC-PUB-15198 system paper, and
the ConfigEvrV2CoreTriggersYaml.pdf Confluence link named in
EvrV2CoreTriggers.py. The repository page and the paper do not describe EVR V2
behavior, and the Confluence link returned no content. No independent SLAC
source was found, so this model is derived only from the shipped VHDL of
EvrV2Pkg, EvrV2Trigger, EvrV2TriggerCompl, EvrV2EventSelect and EvrV2FromV1.
The calibration vectors in the unit tests are captured from that RTL under
GHDL: they are regression pins, not independent evidence. A pointer to a
specification from a maintainer would replace this derivation.

The module uses only the Python standard library and tests.common.timing_model,
so it runs in the common test leg and can be imported by every EVR test.

Cycle convention: ``TriggerModel.step`` is called once per clock with the
inputs that are stable just before a rising edge and returns trigstate as it
reads just after that edge. A cocotb test that sets the inputs right after one
edge and samples the output 2 ns after the next edge compares like with like.
"""

from __future__ import annotations

from tests.common import timing_model

TRIG_WIDTH = 28
TRIGGER_CONFIG_BITS = 87
CHANNEL_CONFIG_BITS = 81

# (name, width, count) in EvrV2Pkg toSlv order, element 0 at the lowest bits.
TRIGGER_CONFIG_FIELDS = (
    ("enabled", 1, 1),
    ("polarity", 1, 1),
    ("complEn", 1, 1),
    ("complAnd", 1, 1),
    ("delay", TRIG_WIDTH, 1),
    ("width", TRIG_WIDTH, 1),
    ("channel", 4, 1),
    ("channels", 16, 1),
    ("delayTap", 6, 1),
    ("loadTap", 1, 1),
)

CHANNEL_CONFIG_FIELDS = (
    ("enabled", 1, 1),
    ("rateSel", 13, 1),
    ("destSel", 19, 1),
    ("bsaEnabled", 1, 1),
    ("bsaActiveSetup", 6, 1),
    ("bsaActiveDelay", 20, 1),
    ("bsaActiveWidth", 20, 1),
    ("dmaEnabled", 1, 1),
)

# EVRV2_TRIGGER_CONFIG_INIT_C and EVRV2_CHANNEL_CONFIG_INIT_C.
TRIGGER_CONFIG_DEFAULTS = {
    "enabled": 0,
    "polarity": 1,
    "complEn": 0,
    "complAnd": 0,
    "delay": 0,
    "width": 1,
    "channel": 0,
    "channels": 0,
    "delayTap": 0,
    "loadTap": 0,
}

CHANNEL_CONFIG_DEFAULTS = {
    "enabled": 0,
    "rateSel": 0,
    "destSel": 0,
    "bsaEnabled": 0,
    "bsaActiveSetup": 0,
    "bsaActiveDelay": 0,
    "bsaActiveWidth": 1,
    "dmaEnabled": 0,
}

# The first active cycle of a trigger is delay + FIRE_TO_RISE_CYCLES cycles
# after the cycle in which fire is high (measured on the RTL).
FIRE_TO_RISE_CYCLES = 4

# A fire that comes fewer than this many cycles after an accepted fire is lost:
# the state machine spends two cycles pushing and re-arming (measured on the RTL).
MIN_FIRE_SPACING = 3


def pack_trigger_config(**fields) -> int:
    """Return the 87-bit vector EvrV2Pkg toSlv produces; missing keys take the defaults."""
    return timing_model.pack_fields(TRIGGER_CONFIG_FIELDS, {**TRIGGER_CONFIG_DEFAULTS, **fields})


def unpack_trigger_config(value: int) -> dict:
    """Return the trigger configuration dictionary toTriggerConfig reads from 87 bits."""
    return timing_model.unpack_fields(TRIGGER_CONFIG_FIELDS, value)


def pack_channel_config(**fields) -> int:
    """Return the 81-bit vector EvrV2Pkg toSlv produces; missing keys take the defaults."""
    return timing_model.pack_fields(CHANNEL_CONFIG_FIELDS, {**CHANNEL_CONFIG_DEFAULTS, **fields})


def unpack_channel_config(value: int) -> dict:
    """Return the channel configuration dictionary toChannelConfig reads from 81 bits."""
    return timing_model.unpack_fields(CHANNEL_CONFIG_FIELDS, value)


def bit_size(n: int) -> int:
    """Return surf StdRtlPkg bitSize: the bits needed to count to ``n``, at least 1."""
    if n < 0:
        raise ValueError(f"bit_size needs a non-negative value, got {n}")
    return max(1, n.bit_length())


def queue_capacity(trig_depth: int) -> int:
    """Return how many pulses EvrV2Trigger accepts while none has left its queue.

    The formula 2 ** bit_size(trig_depth) + 1 is measured at trig_depth 0, 1, 4,
    16, 28 and 127 and only assumed at any other depth. Each pulse takes two
    queue entries (a rising and a falling level), the queue address is
    bit_size(trig_depth) + 1 bits wide, and the entry the trigger logic is
    already counting down is not part of the stored total.
    """
    return 2 ** bit_size(trig_depth) + 1


class _SurfFifoSync:
    """surf FifoSync as EvrV2Trigger instantiates it: sync, block RAM, FWFT, no pipeline stage.

    Every register of FifoWrFsm, FifoRdFsm and the RAM output stage is kept, so
    the write-to-valid latency, the full condition and the loss of a write that
    coincides with reset all follow from the structure.
    """

    def __init__(self, addr_width: int):
        self.mask = (1 << addr_width) - 1
        self.ram: dict[int, int] = {}
        self.ram_reg = 0
        self.dout = 0
        self._reset_registers()

    def _reset_registers(self) -> None:
        self.w_full = 1
        self.w_count = self.mask
        self.w_addr = 0
        self.t_valid = [0, 0]
        self.r_empty = 1
        self.r_addr = 0

    @property
    def valid(self) -> int:
        return self.t_valid[1]

    def step(self, rst: int, wr_en: int, rd_en: int, din: int) -> None:
        mask = self.mask
        t_valid = list(self.t_valid)
        enb = regceb = 0
        r_addr = self.r_addr
        if rd_en:
            t_valid[1] = 0
        if t_valid[1] == 0 and self.t_valid[0] == 1:
            regceb = 1
            t_valid[1] = 1
            t_valid[0] = 0
        if t_valid[0] == 0 and self.r_empty == 0:
            enb = 1
            t_valid[0] = 1
            r_addr = (self.r_addr + 1) & mask
        rd_index = (r_addr - 1) & mask if t_valid[0] else r_addr

        w_addr = self.w_addr
        wr_ack = 0
        if wr_en and self.w_full == 0:
            wr_ack = 1
            w_addr = (self.w_addr + 1) & mask
        w_count = (w_addr - rd_index) & mask
        w_full = 1 if w_count == mask else 0
        r_count = (w_addr - r_addr) & mask
        r_empty = 1 if r_count == 0 else 0

        if wr_ack:
            self.ram[w_addr] = din
        next_dout = self.ram_reg if regceb else self.dout
        if enb:
            self.ram_reg = self.ram.get(r_addr, 0)
        self.dout = next_dout

        if rst:
            self._reset_registers()
        else:
            self.t_valid = t_valid
            self.r_addr = r_addr
            self.r_empty = r_empty
            self.w_addr = w_addr
            self.w_count = w_count
            self.w_full = w_full


class TriggerModel:
    """Cycle-accurate model of EvrV2Trigger, field for field.

    ``trig_depth``, ``channels`` and ``use_mask`` are the entity generics
    TRIG_DEPTH_C, CHANNELS_C and USE_MASK_G; ``trig_width`` is TRIG_WIDTH_C, the
    bit width of the delay and width counters.
    """

    def __init__(self, trig_depth: int = 16, channels: int = 1, use_mask: bool = False, trig_width: int = TRIG_WIDTH):
        self.trig_depth = trig_depth
        self.channels = channels
        self.use_mask = use_mask
        self.trig_width = trig_width
        self.counter_mask = (1 << trig_width) - 1
        self.reset()

    def reset(self) -> None:
        """Return to the power-up state: the registers hold REG_INIT_C."""
        self.fifo = _SurfFifoSync(bit_size(self.trig_depth) + 1)
        self.r = self._init_registers()

    @staticmethod
    def _init_registers() -> dict:
        return {
            "fifo_delay": 0,
            "push_state": "DISABLED",
            "duration": 0,
            "state": 0,
            "next_state": 0,
            "push_width": 0,
            "push_delay": 0,
            "skip": 1,
            "fifoReset": 1,
        }

    def step(self, config: dict, arm: int, fire: int, rst: int = 0) -> int:
        """Advance one clock edge and return trigstate after it."""
        mask = self.counter_mask
        top = self.trig_width
        r = self.r
        v = dict(r)
        fifo_wr = fifo_rd = 0
        fifo_din = 0
        v["fifoReset"] = 0

        delay = config["delay"] & mask
        width = config["width"] & mask
        polarity = config["polarity"]

        if r["duration"] == 0:
            v["state"] = r["next_state"]
            if self.fifo.valid:
                dout = self.fifo.dout
                v["next_state"] = (dout >> top) & 1
                x = dout & mask
                if x == 0:
                    v["state"] = v["next_state"]
                else:
                    v["duration"] = (x - 1) & mask
                fifo_rd = 1
        else:
            v["duration"] = (r["duration"] - 1) & mask

        if r["fifo_delay"] != 0:
            v["fifo_delay"] = (r["fifo_delay"] - 1) & mask

        x = width
        if delay == 0:
            x = (x - 1) & mask
        v["push_width"] = x

        v["skip"] = 0
        if r["fifo_delay"] > delay or width == 0:
            v["skip"] = 1

        v["push_delay"] = (delay + width - 1) & mask

        push_state = r["push_state"]
        if push_state == "DISABLED":
            if config["enabled"]:
                v["push_state"] = "ENABLED"
                fifo_wr = 1
                fifo_din = (1 - polarity) << top
        elif push_state == "ENABLED":
            if self.use_mask:
                armed = (arm & config["channels"] & ((1 << self.channels) - 1)) != 0
            else:
                if config["channel"] >= self.channels:
                    raise ValueError(f"channel {config['channel']} is at or above the {self.channels} channels")
                armed = (arm >> config["channel"]) & 1 == 1
            if armed:
                v["push_state"] = "ARMED"
        elif push_state == "ARMED":
            if fire:
                if r["skip"]:
                    v["push_state"] = "ENABLED"
                else:
                    v["push_state"] = "PUSHING"
                    fifo_wr = 1
                    fifo_din = (polarity << top) | ((delay - r["fifo_delay"]) & mask)
                    v["fifo_delay"] = r["push_delay"]
        elif push_state == "PUSHING":
            fifo_wr = 1
            fifo_din = ((1 - polarity) << top) | r["push_width"]
            v["push_state"] = "ENABLED"

        if rst or not config["enabled"]:
            v = self._init_registers()
            fifo_wr = fifo_rd = 0
            fifo_din = 0

        self.fifo.step(r["fifoReset"], fifo_wr, fifo_rd, fifo_din)
        self.r = v
        return v["state"]
