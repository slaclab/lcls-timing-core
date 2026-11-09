.. _api-evrv2triggerreg:

EvrV2TriggerReg
===============

Source: :repo:`python/LclsTimingCore/EvrV2TriggerReg.py`. Register table: :ref:`EvrV2TriggerReg registers <register-map-evrv2triggerreg>`.

Constructor
-----------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Argument
     - Default
   * - ``name``
     - ``'EvrV2TriggerReg'``
   * - ``description``
     - ``'EVR V2 Trigger'``
   * - ``useTap``
     - ``False``
   * - ``tickUnit``
     - ``'TBD'``
   * - ``**kwargs``
     - none

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
   * - ``Source``
     - RemoteVariable
     - ``0x000``
     - [3:0]
     - RW
     - UInt
     - none
     - Source mask
   * - ``Polarity``
     - RemoteVariable
     - ``0x000``
     - [16]
     - RW
     - enum 0: Falling, 1: Rising
     - none
     - Signal polarity
   * - ``ComplEn``
     - RemoteVariable
     - ``0x000``
     - [29]
     - RW
     - enum 0: Disabled, 1: Enabled
     - none
     - Enable complementary trigger outputs
   * - ``ComplAnd``
     - RemoteVariable
     - ``0x000``
     - [30]
     - RW
     - enum 0: LogicOR, 1: LogicAND
     - none
     - Complementary trigger logic
   * - ``EnableTrig``
     - RemoteVariable
     - ``0x000``
     - [31]
     - RW
     - Bool
     - none
     - Trigger Enable
   * - ``Delay``
     - RemoteVariable
     - ``0x004``
     - [27:0]
     - RW
     - UInt
     - none
     - Delay in ticks
   * - ``Width``
     - RemoteVariable
     - ``0x008``
     - [27:0]
     - RW
     - UInt
     - none
     - Width in ticks

Arguments useTap
~~~~~~~~~~~~~~~~

Constructor arguments: ``useTap=True``.

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
   * - ``Source``
     - RemoteVariable
     - ``0x000``
     - [3:0]
     - RW
     - UInt
     - none
     - Source mask
   * - ``Polarity``
     - RemoteVariable
     - ``0x000``
     - [16]
     - RW
     - enum 0: Falling, 1: Rising
     - none
     - Signal polarity
   * - ``ComplEn``
     - RemoteVariable
     - ``0x000``
     - [29]
     - RW
     - enum 0: Disabled, 1: Enabled
     - none
     - Enable complementary trigger outputs
   * - ``ComplAnd``
     - RemoteVariable
     - ``0x000``
     - [30]
     - RW
     - enum 0: LogicOR, 1: LogicAND
     - none
     - Complementary trigger logic
   * - ``EnableTrig``
     - RemoteVariable
     - ``0x000``
     - [31]
     - RW
     - Bool
     - none
     - Trigger Enable
   * - ``Delay``
     - RemoteVariable
     - ``0x004``
     - [27:0]
     - RW
     - UInt
     - none
     - Delay in ticks
   * - ``Width``
     - RemoteVariable
     - ``0x008``
     - [27:0]
     - RW
     - UInt
     - none
     - Width in ticks
   * - ``DelayTap``
     - RemoteVariable
     - ``0x00C``
     - [5:0]
     - RW
     - UInt
     - ``useTap``
     - Delay tpa in ticks/64 (Only valid register is USE_TAP_C=true)
   * - ``DelayTapReadback``
     - RemoteVariable
     - ``0x00C``
     - [21:16]
     - RO
     - UInt
     - ``useTap``
     - Delay tap readback in ticks/64 (Only valid register is USE_TAP_C=true)

Known issues
------------

none
