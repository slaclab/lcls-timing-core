.. _api-gthrxaligncheck:

GthRxAlignCheck
===============

Source: :repo:`python/LclsTimingCore/GthRxAlignCheck.py`. Register table: :ref:`GthRxAlignCheck registers <register-map-gthrxaligncheck>`.

Constructor
-----------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Argument
     - Default
   * - ``name``
     - ``'GthRxAlignCheck'``
   * - ``description``
     - ``'Timing frame phase lock'``
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
   * - ``PhaseCount[0..63]``
     - RemoteVariable
     - ``0x000`` + ``0x4`` * i
     - [31:0]
     - RO
     - UInt
     - none
     - Timing frame phase
   * - ``PhaseTarget``
     - RemoteVariable
     - ``0x100``
     - [6:0]
     - RW
     - UInt
     - none
     - Timing frame phase lock target
   * - ``Mask``
     - RemoteVariable
     - ``0x100``
     - [14:8]
     - RW
     - UInt
     - none
     - Mask
   * - ``ResetLen``
     - RemoteVariable
     - ``0x100``
     - [19:16]
     - RW
     - UInt
     - none
     - Reset length
   * - ``LastPhase``
     - RemoteVariable
     - ``0x104``
     - [6:0]
     - RO
     - UInt
     - none
     - Last timing frame phase seen
   * - ``TxClkFreqRaw``
     - RemoteVariable
     - ``0x108``
     - [31:0]
     - RO
     - UInt
     - none
     - no description in source
   * - ``RxClkFreqRaw``
     - RemoteVariable
     - ``0x10C``
     - [31:0]
     - RO
     - UInt
     - none
     - no description in source
   * - ``RxClkFreq``
     - LinkVariable
     - none
     - none
     - RO
     - depends on RxClkFreqRaw
     - none
     - no description in source
   * - ``TxClkFreq``
     - LinkVariable
     - none
     - none
     - RO
     - depends on TxClkFreqRaw
     - none
     - no description in source

Known issues
------------

none
