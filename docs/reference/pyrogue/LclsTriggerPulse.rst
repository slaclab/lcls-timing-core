.. _api-lclstriggerpulse:

LclsTriggerPulse
================

Source: :repo:`python/LclsTimingCore/LclsTriggerPulse.py`. Register table: :ref:`LclsTriggerPulse registers <register-map-lclstriggerpulse>`.

Constructor
-----------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Argument
     - Default
   * - ``name``
     - ``'LclsTriggerPulse'``
   * - ``description``
     - ``'Timing trigger pulse configuration'``
   * - ``**kwargs``
     - none

Arguments beyond the ``pr.Device`` defaults: none.

Constructor checks
------------------

none

Sub-devices
-----------

none

Variables
---------

Arguments default
~~~~~~~~~~~~~~~~~

Constructor arguments: none.

.. list-table::
   :header-rows: 1
   :widths: 17 11 12 7 6 14 10 23

   * - Name
     - Kind
     - Offset
     - Bits
     - Mode
     - Base or enum
     - Condition
     - Description
   * - ``OpCodeMask[0..7]``
     - RemoteVariable
     - ``0x000`` + ``0x4`` * i
     - [31:0]
     - RW
     - UInt
     - none
     - Opcode mask 256 bits to connect the pulse to any combination of opcodes
   * - ``PulseDelay``
     - RemoteVariable
     - ``0x020``
     - [31:0]
     - RW
     - UInt
     - none
     - Pulse delay (Number of recovered clock cycles)
   * - ``PulseWidth``
     - RemoteVariable
     - ``0x024``
     - [31:0]
     - RW
     - UInt
     - none
     - Pulse Width (Number of recovered clock cycles)
   * - ``PulsePolarity``
     - RemoteVariable
     - ``0x028``
     - [0]
     - RW
     - UInt
     - none
     - Pulse polarity: 0-Normal. 1-Inverted

Known issues
------------

none
