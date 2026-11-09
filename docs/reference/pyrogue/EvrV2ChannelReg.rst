.. _api-evrv2channelreg:

EvrV2ChannelReg
===============

Source: :repo:`python/LclsTimingCore/EvrV2ChannelReg.py`. Register table: :ref:`EvrV2ChannelReg registers <register-map-evrv2channelreg>`.

Constructor
-----------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Argument
     - Default
   * - ``name``
     - ``'EvrV2ChannelReg'``
   * - ``description``
     - ``'EVR V2 Channel'``
   * - ``dmaEnable``
     - ``False``
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
   * - ``EnableReg``
     - RemoteVariable
     - ``0x000``
     - [0]
     - RW
     - Bool
     - none
     - Enable Register
   * - ``RateSel``
     - RemoteVariable
     - ``0x004``
     - [10:0]
     - RW
     - UInt
     - none
     - Rate select
   * - ``RateType``
     - RemoteVariable
     - ``0x004``
     - [12:11]
     - RW
     - enum 0: FixedRates, 1: AcRates, 2: ControlWord, 3: INVALID
     - none
     - no description in source
   * - ``DestSel``
     - RemoteVariable
     - ``0x004``
     - [28:13]
     - RW
     - UInt
     - none
     - Destination select
   * - ``DestType``
     - RemoteVariable
     - ``0x004``
     - [30:29]
     - RW
     - enum 2: All, 0: BeamRequest, 1: NotBeamRequest, 3: Invalid
     - none
     - no description in source
   * - ``Count``
     - RemoteVariable
     - ``0x008``
     - [31:0]
     - RO
     - UInt
     - none
     - Counts

Arguments dmaEnable
~~~~~~~~~~~~~~~~~~~

Constructor arguments: ``dmaEnable=True``.

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
   * - ``EnableReg``
     - RemoteVariable
     - ``0x000``
     - [0]
     - RW
     - Bool
     - none
     - Enable Register
   * - ``BsaEnabled``
     - RemoteVariable
     - ``0x000``
     - [1]
     - RW
     - Bool
     - ``dmaEnable``
     - BSA Enable register (Only valid register is DMA_ENABLE_G=true)
   * - ``dmaEnabled``
     - RemoteVariable
     - ``0x000``
     - [2]
     - RW
     - Bool
     - ``dmaEnable``
     - DMA Enable register (Only valid register is DMA_ENABLE_G=true)
   * - ``RateSel``
     - RemoteVariable
     - ``0x004``
     - [10:0]
     - RW
     - UInt
     - none
     - Rate select
   * - ``RateType``
     - RemoteVariable
     - ``0x004``
     - [12:11]
     - RW
     - enum 0: FixedRates, 1: AcRates, 2: ControlWord, 3: INVALID
     - none
     - no description in source
   * - ``DestSel``
     - RemoteVariable
     - ``0x004``
     - [28:13]
     - RW
     - UInt
     - none
     - Destination select
   * - ``DestType``
     - RemoteVariable
     - ``0x004``
     - [30:29]
     - RW
     - enum 2: All, 0: BeamRequest, 1: NotBeamRequest, 3: Invalid
     - none
     - no description in source
   * - ``Count``
     - RemoteVariable
     - ``0x008``
     - [31:0]
     - RO
     - UInt
     - none
     - Counts
   * - ``BsaWindowDelay``
     - RemoteVariable
     - ``0x00C``
     - [19:0]
     - RW
     - UInt
     - ``dmaEnable``
     - Start of BSA sensitivity window following trigger (Only valid register is DMA_ENABLE_G=true)
   * - ``BsaWindowSetup``
     - RemoteVariable
     - ``0x00C``
     - [25:20]
     - RW
     - UInt
     - ``dmaEnable``
     - Start of BSA sensitivity window before trigger (Only valid register is DMA_ENABLE_G=true)
   * - ``BsaWindowWidth``
     - RemoteVariable
     - ``0x010``
     - [19:0]
     - RW
     - UInt
     - ``dmaEnable``
     - Width of BSA sensitivity window (Only valid register is DMA_ENABLE_G=true)

Known issues
------------

none
