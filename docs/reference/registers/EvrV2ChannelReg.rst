.. _register-map-evrv2channelreg:

EvrV2ChannelReg registers
=========================

Decode file: :repo:`LCLS-II/evr/rtl/EvrV2ChannelReg.vhd`. Python class: :repo:`python/LclsTimingCore/EvrV2ChannelReg.py`. YAML map: :repo:`yaml/EvrV2ChannelReg.yaml`.

Variant default
---------------

RTL generics: ``NCHANNELS_G`` = ``1``, ``EVR_CARD_G`` = ``False``, ``DMA_ENABLE_G`` = ``False``. Python arguments: none.

.. list-table::
   :header-rows: 1
   :widths: 9 17 7 6 12 15 15 19

   * - Offset
     - Field
     - Bits
     - Mode
     - Reset
     - Python
     - YAML
     - Description
   * - ``0x000``
     - ``EnableReg``
       RTL: ``enabled``
     - [0]
     - RW
     - ``0x0``
     - agrees
     - not compared
     - Enable Register
   * - ``0x004``
     - ``RateSel``
       RTL: ``rateSel``
     - [12:0]
     - RW
     - ``0x0000``
     - differs: bitSize :issue:`215`
       at 0x004 [10:0] RW
     - not compared
     - Rate select
   * - ``0x004``
     - ``RateType``
     - [12:11]
     - RW
     - ``0x0``
     - differs: missing-in-vhdl :issue:`215`
       at 0x004 [12:11] RW
     - not compared
     - no description in source
   * - ``0x004``
     - ``DestSel``
       RTL: ``destSel``
     - [31:13]
     - RW
     - ``0x00000``
     - differs: bitSize :issue:`215`
       at 0x004 [28:13] RW
     - not compared
     - Destination select
   * - ``0x004``
     - ``DestType``
     - [30:29]
     - RW
     - ``0x0``
     - differs: missing-in-vhdl :issue:`215`
       at 0x004 [30:29] RW
     - not compared
     - no description in source
   * - ``0x008``
     - ``Count``
       RTL: ``eventCount``
     - [31:0]
     - RO
     - ``0x00000000``
     - agrees
     - not compared
     - Counts

Variant dmaEnable
-----------------

RTL generics: ``NCHANNELS_G`` = ``1``, ``EVR_CARD_G`` = ``False``, ``DMA_ENABLE_G`` = ``True``. Python arguments: ``dmaEnable=True``.

.. list-table::
   :header-rows: 1
   :widths: 9 17 7 6 12 15 15 19

   * - Offset
     - Field
     - Bits
     - Mode
     - Reset
     - Python
     - YAML
     - Description
   * - ``0x000``
     - ``EnableReg``
       RTL: ``enabled``
       YAML: ``Enable``
     - [0]
     - RW
     - ``0x0``
     - agrees
     - agrees
     - Enable Register
   * - ``0x000``
     - ``BsaEnabled``
       RTL: ``bsaEnabled``
     - [1]
     - RW
     - ``0x0``
     - agrees
     - agrees
     - BSA Enable register (Only valid register is DMA_ENABLE_G=true)
   * - ``0x000``
     - ``dmaEnabled``
       YAML: ``DmaEnabled``
     - [2]
     - RW
     - ``0x0``
     - agrees
     - agrees
     - DMA Enable register (Only valid register is DMA_ENABLE_G=true)
   * - ``0x004``
     - ``RateSel``
       RTL: ``rateSel``
     - [12:0]
     - RW
     - ``0x0000``
     - differs: bitSize :issue:`215`
       at 0x004 [10:0] RW
     - differs from Python: bitSize :issue:`215`
       at 0x004 [12:0] RW
     - Rate select
   * - ``0x004``
     - ``RateType``
     - [12:11]
     - RW
     - ``0x0``
     - differs: missing-in-vhdl :issue:`215`
       at 0x004 [12:11] RW
     - absent :issue:`215`
     - no description in source
   * - ``0x004``
     - ``DestSel``
       RTL: ``destSel``
     - [31:13]
     - RW
     - ``0x00000``
     - differs: bitSize :issue:`215`
       at 0x004 [28:13] RW
     - differs from Python: bitSize :issue:`215`
       at 0x004 [31:13] RW
     - Destination select
   * - ``0x004``
     - ``DestType``
     - [30:29]
     - RW
     - ``0x0``
     - differs: missing-in-vhdl :issue:`215`
       at 0x004 [30:29] RW
     - absent :issue:`215`
     - no description in source
   * - ``0x008``
     - ``Count``
       RTL: ``eventCount``
     - [31:0]
     - RO
     - ``0x00000000``
     - agrees
     - agrees
     - Counts
   * - ``0x00C``
     - ``BsaWindowDelay``
       RTL: ``bsaActiveDelay``
     - [19:0]
     - RW
     - ``0x00000``
     - agrees
     - agrees
     - Start of BSA sensitivity window following trigger (Only valid register is DMA_ENABLE_G=true)
   * - ``0x00C``
     - ``BsaWindowSetup``
       RTL: ``bsaActiveSetup``
     - [25:20]
     - RW
     - ``0x00``
     - agrees
     - agrees
     - Start of BSA sensitivity window before trigger (Only valid register is DMA_ENABLE_G=true)
   * - ``0x010``
     - ``BsaWindowWidth``
       RTL: ``bsaActiveWidth``
     - [19:0]
     - RW
     - ``0x00001``
     - agrees
     - agrees
     - Width of BSA sensitivity window (Only valid register is DMA_ENABLE_G=true)

Known differences
-----------------

The comparison of the sources reports these differences, each recorded against an issue.

.. warning::

   The sources disagree on the following registers; treat the RTL as the measured behavior.

   * ``DestSel`` (bitSize): ``DestSel python width 16 vs vhdl width 19`` :issue:`215`
   * ``DestType`` (missing-in-vhdl): ``DestType is in python at bit 61 (width 2) but not in vhdl`` :issue:`215`
   * ``DestType`` (missing-in-yaml): ``DestType is in python at bit 61 (width 2) but not in yaml`` :issue:`215`
   * ``RateSel`` (bitSize): ``RateSel python width 11 vs vhdl width 13`` :issue:`215`
   * ``RateType`` (missing-in-vhdl): ``RateType is in python at bit 43 (width 2) but not in vhdl`` :issue:`215`
   * ``RateType`` (missing-in-yaml): ``RateType is in python at bit 43 (width 2) but not in yaml`` :issue:`215`
