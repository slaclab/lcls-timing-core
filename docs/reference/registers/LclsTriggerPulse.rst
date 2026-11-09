.. _register-map-lclstriggerpulse:

LclsTriggerPulse registers
==========================

No RTL in repo: the firmware that implements this block lives outside this repository, so the tables show the PyRogue declarations and how the YAML map agrees with them.

Python class: :repo:`python/LclsTimingCore/LclsTriggerPulse.py`. YAML map: :repo:`yaml/LclsTriggerPulse.yaml`.

Variant default
---------------

Python arguments: none.

.. list-table::
   :header-rows: 1
   :widths: 10 22 8 7 23 30

   * - Offset
     - Field
     - Bits
     - Mode
     - YAML
     - Description
   * - ``0x000`` + ``0x4`` * i
     - ``OpCodeMask[0..7]``
     - [31:0]
     - RW
     - agrees
     - Opcode mask 256 bits to connect the pulse to any combination of opcodes
   * - ``0x020``
     - ``PulseDelay``
     - [31:0]
     - RW
     - agrees
     - Pulse delay (Number of recovered clock cycles)
   * - ``0x024``
     - ``PulseWidth``
     - [31:0]
     - RW
     - agrees
     - Pulse Width (Number of recovered clock cycles)
   * - ``0x028``
     - ``PulsePolarity``
     - [0]
     - RW
     - agrees
     - Pulse polarity: 0-Normal. 1-Inverted

