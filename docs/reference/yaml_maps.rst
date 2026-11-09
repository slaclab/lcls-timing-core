YAML register maps
==================

The maps in ``yaml/`` are CPSW register descriptions. Each one mirrors a PyRogue class of the same name (the ``drift`` maps, compared field by field on the register pages) or describes a block with no PyRogue class here (the ``shape`` maps). A line ``#include <file>`` pulls in another map before the YAML is parsed, so an including map lists the fields it splices in. The fields are flattened with the CPSW defaults: offset 0, ``nelms`` 1, ``stride`` 0, ``lsBit`` 0, and ``sizeBits`` 32. An array is one row with its element step. A map that does not parse is shown with its error and its issue instead of fields.

.. list-table::
   :header-rows: 1
   :widths: 22 12 14 30 22

   * - File
     - Classification
     - Parses
     - Includes
     - Register page
   * - :ref:`AmcCarrierDRAM.yaml <yaml-map-amccarrierdram>`
     - shape
     - yes
     - none
     - :doc:`YAML-only register maps <registers/yaml_only>`
   * - :ref:`BldAxiStream.yaml <yaml-map-bldaxistream>`
     - shape
     - yes
     - none
     - :doc:`YAML-only register maps <registers/yaml_only>`
   * - :ref:`EvrV1Isr.yaml <yaml-map-evrv1isr>`
     - drift
     - yes
     - none
     - :ref:`EvrV1Isr registers <register-map-evrv1isr>`
   * - :ref:`EvrV1Reg.yaml <yaml-map-evrv1reg>`
     - drift
     - yes
     - none
     - :ref:`EvrV1Reg registers <register-map-evrv1reg>`
   * - :ref:`EvrV2ChannelReg.yaml <yaml-map-evrv2channelreg>`
     - drift
     - yes
     - none
     - :ref:`EvrV2ChannelReg registers <register-map-evrv2channelreg>`
   * - :ref:`EvrV2Core.yaml <yaml-map-evrv2core>`
     - drift
     - yes
     - ``EvrV2PulsegenRegs.yaml``
     - :ref:`EvrV2Core registers <register-map-evrv2core>`
   * - :ref:`EvrV2CoreTriggers.yaml <yaml-map-evrv2coretriggers>`
     - drift
     - yes
     - ``EvrV2ChannelReg.yaml``, ``EvrV2TriggerReg.yaml``
     - :ref:`EvrV2CoreTriggers registers <register-map-evrv2coretriggers>`
   * - :ref:`EvrV2Module.yaml <yaml-map-evrv2module>`
     - shape
     - yes
     - none
     - :doc:`YAML-only register maps <registers/yaml_only>`
   * - :ref:`EvrV2PulsegenRegs.yaml <yaml-map-evrv2pulsegenregs>`
     - shape
     - yes
     - none
     - :doc:`YAML-only register maps <registers/yaml_only>`
   * - :ref:`EvrV2TriggerPulse.yaml <yaml-map-evrv2triggerpulse>`
     - shape
     - yes
     - ``EvrV2PulsegenRegs.yaml``
     - :doc:`YAML-only register maps <registers/yaml_only>`
   * - :ref:`EvrV2TriggerReg.yaml <yaml-map-evrv2triggerreg>`
     - drift
     - yes
     - none
     - :ref:`EvrV2TriggerReg registers <register-map-evrv2triggerreg>`
   * - :ref:`GthRxAlignCheck.yaml <yaml-map-gthrxaligncheck>`
     - drift
     - yes
     - none
     - :ref:`GthRxAlignCheck registers <register-map-gthrxaligncheck>`
   * - :ref:`LclsTriggerPulse.yaml <yaml-map-lclstriggerpulse>`
     - drift
     - yes
     - none
     - :ref:`LclsTriggerPulse registers <register-map-lclstriggerpulse>`
   * - :ref:`TPG.yaml <yaml-map-tpg>`
     - drift
     - no: ``ScannerError``
     - ``TPGControl.yaml``, ``TPGStatus.yaml``, ``TPGSeqState.yaml``, ``TPGSeqJump.yaml``, ``TPGSeqMem.yaml`` (missing)
     - :ref:`TPG registers <register-map-tpg>`
   * - :ref:`TPGControl.yaml <yaml-map-tpgcontrol>`
     - drift
     - no: ``ScannerError``
     - none
     - :ref:`TPGControl registers <register-map-tpgcontrol>`
   * - :ref:`TPGMiniCore.yaml <yaml-map-tpgminicore>`
     - drift
     - yes
     - none
     - :ref:`TPGMiniCore registers <register-map-tpgminicore>`
   * - :ref:`TPGSeqJump.yaml <yaml-map-tpgseqjump>`
     - drift
     - yes
     - none
     - :ref:`TPGSeqJump registers <register-map-tpgseqjump>`
   * - :ref:`TPGSeqState.yaml <yaml-map-tpgseqstate>`
     - drift
     - no: ``ScannerError``
     - none
     - :ref:`TPGSeqState registers <register-map-tpgseqstate>`
   * - :ref:`TPGStatus.yaml <yaml-map-tpgstatus>`
     - drift
     - yes
     - none
     - :ref:`TPGStatus registers <register-map-tpgstatus>`
   * - :ref:`TimingFrameRx.yaml <yaml-map-timingframerx>`
     - drift
     - yes
     - none
     - :ref:`TimingFrameRx registers <register-map-timingframerx>`

.. _yaml-map-amccarrierdram:

AmcCarrierDRAM.yaml
-------------------

YAML map: :repo:`yaml/AmcCarrierDRAM.yaml`.

Classification: ``shape`` (checked for structure only). Register page: :doc:`YAML-only register maps <registers/yaml_only>`.

Includes: none.

Parse status: parses.

Top-level nodes: ``AmcCarrierDRAM`` (MMIODev).

.. list-table::
   :header-rows: 1
   :widths: 40 25 15 20

   * - Field
     - Offset
     - Bits
     - Mode
   * - ``dram[0..536870911]``
     - ``0x000`` + ``0x8`` * i
     - [63:0]
     - RW

.. _yaml-map-bldaxistream:

BldAxiStream.yaml
-----------------

YAML map: :repo:`yaml/BldAxiStream.yaml`.

Classification: ``shape`` (checked for structure only). Register page: :doc:`YAML-only register maps <registers/yaml_only>`.

Includes: none.

Parse status: parses.

Top-level nodes: ``BldAxiStream`` (MMIODev).

.. list-table::
   :header-rows: 1
   :widths: 40 25 15 20

   * - Field
     - Offset
     - Bits
     - Mode
   * - ``PacketSize``
     - ``0x000``
     - [11:0]
     - RW
   * - ``Enable``
     - ``0x000``
     - [31]
     - RW
   * - ``ChannelMask``
     - ``0x004``
     - [30:0]
     - RW
   * - ``ChannelSevr``
     - ``0x008``
     - [61:0]
     - RW
   * - ``WordCount``
     - ``0x010``
     - [11:0]
     - RO
   * - ``TxState``
     - ``0x010``
     - [19:16]
     - RO
   * - ``PulseIdL``
     - ``0x014``
     - [19:0]
     - RO
   * - ``TimeStampL``
     - ``0x018``
     - [31:0]
     - RO
   * - ``Delta``
     - ``0x01C``
     - [31:0]
     - RO
   * - ``PacketCount``
     - ``0x020``
     - [19:0]
     - RO
   * - ``Paused``
     - ``0x020``
     - [31]
     - RO

.. _yaml-map-evrv1isr:

EvrV1Isr.yaml
-------------

YAML map: :repo:`yaml/EvrV1Isr.yaml`.

Classification: ``drift`` (compared with the PyRogue class and the RTL decode). Register page: :ref:`EvrV1Isr registers <register-map-evrv1isr>`.

Includes: none.

Parse status: parses.

Top-level nodes: ``EvrV1Isr`` (MMIODev).

.. list-table::
   :header-rows: 1
   :widths: 40 25 15 20

   * - Field
     - Offset
     - Bits
     - Mode
   * - ``IsrSelect``
     - ``0x000``
     - [0]
     - RW

.. _yaml-map-evrv1reg:

EvrV1Reg.yaml
-------------

YAML map: :repo:`yaml/EvrV1Reg.yaml`.

Classification: ``drift`` (compared with the PyRogue class and the RTL decode). Register page: :ref:`EvrV1Reg registers <register-map-evrv1reg>`.

Includes: none.

Parse status: parses.

Top-level nodes: ``EvrV1Reg`` (MMIODev).

.. list-table::
   :header-rows: 1
   :widths: 40 25 15 20

   * - Field
     - Offset
     - Bits
     - Mode
   * - ``Status``
     - ``0x000``
     - [31:0]
     - RO
   * - ``Control``
     - ``0x004``
     - [31:0]
     - RW
   * - ``IrqFlag``
     - ``0x008``
     - [31:0]
     - RW
   * - ``IrqEnable``
     - ``0x00C``
     - [31:0]
     - RW
   * - ``PulseIrqMap``
     - ``0x010``
     - [31:0]
     - RW
   * - ``PcieIntEna``
     - ``0x014``
     - [31:0]
     - RW
   * - ``FWVersion``
     - ``0x02C``
     - [31:0]
     - RO
   * - ``FWVersionUnmasked``
     - ``0x030``
     - [31:0]
     - RO
   * - ``UsecDivider``
     - ``0x04C``
     - [31:0]
     - RW
   * - ``SecSR``
     - ``0x05C``
     - [31:0]
     - RO
   * - ``SecCounter``
     - ``0x060``
     - [31:0]
     - RO
   * - ``EventCounter``
     - ``0x064``
     - [31:0]
     - RO
   * - ``SecLatch``
     - ``0x068``
     - [31:0]
     - RO
   * - ``EvCntLatch``
     - ``0x06C``
     - [31:0]
     - RO
   * - ``IntEventEn``
     - ``0x0A0``
     - [31:0]
     - RW
   * - ``IntEventCount``
     - ``0x0A4``
     - [0]
     - RW
   * - ``IntEventCode``
     - ``0x0A8``
     - [7:0]
     - RW
   * - ``ExtEventEn``
     - ``0x0AC``
     - [0]
     - RW
   * - ``ExtEventCode``
     - ``0x0B0``
     - [7:0]
     - RW
   * - ``Pulse00[0..3]``
     - ``0x200`` + ``0x0`` * i
     - [31:0]
     - RW
   * - ``Pulse01[0..3]``
     - ``0x210`` + ``0x0`` * i
     - [31:0]
     - RW
   * - ``Pulse02[0..3]``
     - ``0x220`` + ``0x0`` * i
     - [31:0]
     - RW
   * - ``Pulse03[0..3]``
     - ``0x230`` + ``0x0`` * i
     - [31:0]
     - RW
   * - ``Pulse04[0..3]``
     - ``0x240`` + ``0x0`` * i
     - [31:0]
     - RW
   * - ``Pulse05[0..3]``
     - ``0x250`` + ``0x0`` * i
     - [31:0]
     - RW
   * - ``Pulse06[0..3]``
     - ``0x260`` + ``0x0`` * i
     - [31:0]
     - RW
   * - ``Pulse07[0..3]``
     - ``0x270`` + ``0x0`` * i
     - [31:0]
     - RW
   * - ``Pulse08[0..3]``
     - ``0x280`` + ``0x0`` * i
     - [31:0]
     - RW
   * - ``Pulse09[0..3]``
     - ``0x290`` + ``0x0`` * i
     - [31:0]
     - RW
   * - ``Pulse10[0..3]``
     - ``0x2A0`` + ``0x0`` * i
     - [31:0]
     - RW
   * - ``Pulse11[0..3]``
     - ``0x2B0`` + ``0x0`` * i
     - [31:0]
     - RW
   * - ``OutputMap[0..11]``
     - ``0x440`` + ``0x0`` * i
     - [15:0]
     - RW
   * - ``MapRam1[0..1023]``
     - ``0x4000`` + ``0x0`` * i
     - [31:0]
     - RO
   * - ``MapRam2[0..1023]``
     - ``0x6000`` + ``0x0`` * i
     - [31:0]
     - RO

.. _yaml-map-evrv2channelreg:

EvrV2ChannelReg.yaml
--------------------

YAML map: :repo:`yaml/EvrV2ChannelReg.yaml`.

Classification: ``drift`` (compared with the PyRogue class and the RTL decode). Register page: :ref:`EvrV2ChannelReg registers <register-map-evrv2channelreg>`.

Includes: none.

Parse status: parses.

Top-level nodes: ``EvrV2ChannelReg`` (MMIODev).

.. list-table::
   :header-rows: 1
   :widths: 40 25 15 20

   * - Field
     - Offset
     - Bits
     - Mode
   * - ``Enable``
     - ``0x000``
     - [0]
     - RW
   * - ``BsaEnabled``
     - ``0x000``
     - [1]
     - RW
   * - ``DmaEnabled``
     - ``0x000``
     - [2]
     - RW
   * - ``RateSel``
     - ``0x004``
     - [12:0]
     - RW
   * - ``DestSel``
     - ``0x004``
     - [31:13]
     - RW
   * - ``Count``
     - ``0x008``
     - [31:0]
     - RO
   * - ``BsaWindowDelay``
     - ``0x00C``
     - [19:0]
     - RW
   * - ``BsaWindowSetup``
     - ``0x00C``
     - [25:20]
     - RW
   * - ``BsaWindowWidth``
     - ``0x010``
     - [19:0]
     - RW

.. _yaml-map-evrv2core:

EvrV2Core.yaml
--------------

YAML map: :repo:`yaml/EvrV2Core.yaml`.

Classification: ``drift`` (compared with the PyRogue class and the RTL decode). Register page: :ref:`EvrV2Core registers <register-map-evrv2core>`.

Includes:

* ``EvrV2PulsegenRegs.yaml``

Parse status: parses.

Top-level nodes: ``EvrV2PulsegenRegs`` (no class), ``EvrV2Core`` (MMIODev).

The fields include those spliced in from ``EvrV2PulsegenRegs.yaml``.

.. list-table::
   :header-rows: 1
   :widths: 40 25 15 20

   * - Field
     - Offset
     - Bits
     - Mode
   * - ``IrqEnable``
     - ``0x000``
     - [0]
     - RW
   * - ``IrqStatus``
     - ``0x004``
     - [0]
     - RO
   * - ``LinkAddr``
     - ``0x008``
     - [15:0]
     - RO
   * - ``GtxDebug``
     - ``0x00C``
     - [7:0]
     - RO
   * - ``CountReset``
     - ``0x010``
     - [0]
     - RW
   * - ``ModeSel``
     - ``0x014``
     - [0]
     - RW
   * - ``DmaFullThr``
     - ``0x018``
     - [23:0]
     - RW
   * - ``ChannelEnable[0..11]``
     - ``0x020`` + ``0x20`` * i
     - [0]
     - RW
   * - ``ChannelBsaEnable[0..11]``
     - ``0x020`` + ``0x20`` * i
     - [1]
     - RW
   * - ``ChannelDmaEnable[0..11]``
     - ``0x020`` + ``0x20`` * i
     - [2]
     - RW
   * - ``ChannelRateSel[0..11]``
     - ``0x024`` + ``0x20`` * i
     - [12:0]
     - RW
   * - ``ChannelDestSel[0..11]``
     - ``0x024`` + ``0x20`` * i
     - [30:13]
     - RW
   * - ``ChannelEventCnt[0..11]``
     - ``0x028`` + ``0x20`` * i
     - [31:0]
     - RW
   * - ``ChannelBsaDelay[0..11]``
     - ``0x02C`` + ``0x20`` * i
     - [19:0]
     - RW
   * - ``ChannelBsaSetup[0..11]``
     - ``0x02C`` + ``0x20`` * i
     - [31:20]
     - RW
   * - ``ChannelBsaWidth[0..11]``
     - ``0x030`` + ``0x20`` * i
     - [19:0]
     - RW
   * - ``GlobalEventCnt``
     - ``0x1A8``
     - [31:0]
     - RW
   * - ``TriggerChannel[0..11]``
     - ``0x200`` + ``0x10`` * i
     - [3:0]
     - RW
   * - ``TriggerPolarity[0..11]``
     - ``0x200`` + ``0x10`` * i
     - [16]
     - RW
   * - ``TriggerEnable[0..11]``
     - ``0x200`` + ``0x10`` * i
     - [31]
     - RW
   * - ``TriggerDelay[0..11]``
     - ``0x204`` + ``0x10`` * i
     - [27:0]
     - RW
   * - ``TriggerWidth[0..11]``
     - ``0x208`` + ``0x10`` * i
     - [27:0]
     - RW
   * - ``TriggerFineDelay[0..11]``
     - ``0x20C`` + ``0x10`` * i
     - [5:0]
     - RW

.. _yaml-map-evrv2coretriggers:

EvrV2CoreTriggers.yaml
----------------------

YAML map: :repo:`yaml/EvrV2CoreTriggers.yaml`.

Classification: ``drift`` (compared with the PyRogue class and the RTL decode). Register page: :ref:`EvrV2CoreTriggers registers <register-map-evrv2coretriggers>`.

Includes:

* ``EvrV2ChannelReg.yaml``
* ``EvrV2TriggerReg.yaml``

Parse status: parses.

Top-level nodes: ``EvrV2ChannelReg`` (MMIODev), ``EvrV2TriggerReg`` (MMIODev), ``EvrV2CoreTriggers`` (MMIODev).

The fields include those spliced in from ``EvrV2ChannelReg.yaml``, ``EvrV2TriggerReg.yaml``.

.. list-table::
   :header-rows: 1
   :widths: 40 25 15 20

   * - Field
     - Offset
     - Bits
     - Mode
   * - ``EvrV2ChannelReg[0..15].Enable``
     - ``0x000`` + ``0x100`` * i
     - [0]
     - RW
   * - ``EvrV2ChannelReg[0..15].BsaEnabled``
     - ``0x000`` + ``0x100`` * i
     - [1]
     - RW
   * - ``EvrV2ChannelReg[0..15].DmaEnabled``
     - ``0x000`` + ``0x100`` * i
     - [2]
     - RW
   * - ``EvrV2ChannelReg[0..15].RateSel``
     - ``0x004`` + ``0x100`` * i
     - [12:0]
     - RW
   * - ``EvrV2ChannelReg[0..15].DestSel``
     - ``0x004`` + ``0x100`` * i
     - [31:13]
     - RW
   * - ``EvrV2ChannelReg[0..15].Count``
     - ``0x008`` + ``0x100`` * i
     - [31:0]
     - RO
   * - ``EvrV2ChannelReg[0..15].BsaWindowDelay``
     - ``0x00C`` + ``0x100`` * i
     - [19:0]
     - RW
   * - ``EvrV2ChannelReg[0..15].BsaWindowSetup``
     - ``0x00C`` + ``0x100`` * i
     - [25:20]
     - RW
   * - ``EvrV2ChannelReg[0..15].BsaWindowWidth``
     - ``0x010`` + ``0x100`` * i
     - [19:0]
     - RW
   * - ``EvrV2TriggerReg[0..15].Source``
     - ``0x1000`` + ``0x100`` * i
     - [3:0]
     - RW
   * - ``EvrV2TriggerReg[0..15].Polarity``
     - ``0x1000`` + ``0x100`` * i
     - [16]
     - RW
   * - ``EvrV2TriggerReg[0..15].ComplEn``
     - ``0x1000`` + ``0x100`` * i
     - [28]
     - RW
   * - ``EvrV2TriggerReg[0..15].ComplAnd``
     - ``0x1000`` + ``0x100`` * i
     - [29]
     - RW
   * - ``EvrV2TriggerReg[0..15].Enable``
     - ``0x1000`` + ``0x100`` * i
     - [31]
     - RW
   * - ``EvrV2TriggerReg[0..15].Delay``
     - ``0x1004`` + ``0x100`` * i
     - [27:0]
     - RW
   * - ``EvrV2TriggerReg[0..15].Width``
     - ``0x1008`` + ``0x100`` * i
     - [27:0]
     - RW
   * - ``EvrV2TriggerReg[0..15].DelayTap``
     - ``0x100C`` + ``0x100`` * i
     - [5:0]
     - RW
   * - ``EvrV2TriggerReg[0..15].DelayTapReadback``
     - ``0x100C`` + ``0x100`` * i
     - [21:16]
     - RO

.. _yaml-map-evrv2module:

EvrV2Module.yaml
----------------

YAML map: :repo:`yaml/EvrV2Module.yaml`.

Classification: ``shape`` (checked for structure only). Register page: :doc:`YAML-only register maps <registers/yaml_only>`.

Includes: none.

Parse status: parses.

Top-level nodes: ``Device`` (no class).

The fields cannot be listed: ``EvrV2Module.yaml has no top-level key 'EvrV2Module'``.

.. _yaml-map-evrv2pulsegenregs:

EvrV2PulsegenRegs.yaml
----------------------

YAML map: :repo:`yaml/EvrV2PulsegenRegs.yaml`.

Classification: ``shape`` (checked for structure only). Register page: :doc:`YAML-only register maps <registers/yaml_only>`.

Includes: none.

Parse status: parses.

Top-level nodes: ``EvrV2PulsegenRegs`` (no class).

.. list-table::
   :header-rows: 1
   :widths: 40 25 15 20

   * - Field
     - Offset
     - Bits
     - Mode
   * - ``LinkAddr``
     - ``0x008``
     - [15:0]
     - RO
   * - ``GtxDebug``
     - ``0x00C``
     - [7:0]
     - RO
   * - ``CountReset``
     - ``0x010``
     - [0]
     - RW
   * - ``ModeSel``
     - ``0x014``
     - [0]
     - RW
   * - ``ChannelEnable[0..11]``
     - ``0x020`` + ``0x20`` * i
     - [0]
     - RW
   * - ``ChannelRateSel[0..11]``
     - ``0x024`` + ``0x20`` * i
     - [12:0]
     - RW
   * - ``ChannelDestSel[0..11]``
     - ``0x024`` + ``0x20`` * i
     - [30:13]
     - RW
   * - ``ChannelEventCnt[0..11]``
     - ``0x028`` + ``0x20`` * i
     - [31:0]
     - RW
   * - ``GlobalEventCnt``
     - ``0x1A8``
     - [31:0]
     - RW
   * - ``TriggerChannel[0..11]``
     - ``0x200`` + ``0x10`` * i
     - [3:0]
     - RW
   * - ``TriggerPolarity[0..11]``
     - ``0x200`` + ``0x10`` * i
     - [16]
     - RW
   * - ``TriggerEnable[0..11]``
     - ``0x200`` + ``0x10`` * i
     - [31]
     - RW
   * - ``TriggerDelay[0..11]``
     - ``0x204`` + ``0x10`` * i
     - [27:0]
     - RW
   * - ``TriggerWidth[0..11]``
     - ``0x208`` + ``0x10`` * i
     - [27:0]
     - RW
   * - ``TriggerFineDelay[0..11]``
     - ``0x20C`` + ``0x10`` * i
     - [5:0]
     - RW

.. _yaml-map-evrv2triggerpulse:

EvrV2TriggerPulse.yaml
----------------------

YAML map: :repo:`yaml/EvrV2TriggerPulse.yaml`.

Classification: ``shape`` (checked for structure only). Register page: :doc:`YAML-only register maps <registers/yaml_only>`.

Includes:

* ``EvrV2PulsegenRegs.yaml``

Parse status: parses.

Top-level nodes: ``EvrV2PulsegenRegs`` (no class), ``EvrV2TriggerPulse`` (MMIODev).

The fields include those spliced in from ``EvrV2PulsegenRegs.yaml``.

.. list-table::
   :header-rows: 1
   :widths: 40 25 15 20

   * - Field
     - Offset
     - Bits
     - Mode
   * - ``LinkAddr``
     - ``0x008``
     - [15:0]
     - RO
   * - ``GtxDebug``
     - ``0x00C``
     - [7:0]
     - RO
   * - ``CountReset``
     - ``0x010``
     - [0]
     - RW
   * - ``ModeSel``
     - ``0x014``
     - [0]
     - RW
   * - ``ChannelEnable[0..11]``
     - ``0x020`` + ``0x20`` * i
     - [0]
     - RW
   * - ``ChannelRateSel[0..11]``
     - ``0x024`` + ``0x20`` * i
     - [12:0]
     - RW
   * - ``ChannelDestSel[0..11]``
     - ``0x024`` + ``0x20`` * i
     - [30:13]
     - RW
   * - ``ChannelEventCnt[0..11]``
     - ``0x028`` + ``0x20`` * i
     - [31:0]
     - RW
   * - ``GlobalEventCnt``
     - ``0x1A8``
     - [31:0]
     - RW
   * - ``TriggerChannel[0..11]``
     - ``0x200`` + ``0x10`` * i
     - [3:0]
     - RW
   * - ``TriggerPolarity[0..11]``
     - ``0x200`` + ``0x10`` * i
     - [16]
     - RW
   * - ``TriggerEnable[0..11]``
     - ``0x200`` + ``0x10`` * i
     - [31]
     - RW
   * - ``TriggerDelay[0..11]``
     - ``0x204`` + ``0x10`` * i
     - [27:0]
     - RW
   * - ``TriggerWidth[0..11]``
     - ``0x208`` + ``0x10`` * i
     - [27:0]
     - RW
   * - ``TriggerFineDelay[0..11]``
     - ``0x20C`` + ``0x10`` * i
     - [5:0]
     - RW

.. _yaml-map-evrv2triggerreg:

EvrV2TriggerReg.yaml
--------------------

YAML map: :repo:`yaml/EvrV2TriggerReg.yaml`.

Classification: ``drift`` (compared with the PyRogue class and the RTL decode). Register page: :ref:`EvrV2TriggerReg registers <register-map-evrv2triggerreg>`.

Includes: none.

Parse status: parses.

Top-level nodes: ``EvrV2TriggerReg`` (MMIODev).

.. list-table::
   :header-rows: 1
   :widths: 40 25 15 20

   * - Field
     - Offset
     - Bits
     - Mode
   * - ``Source``
     - ``0x000``
     - [3:0]
     - RW
   * - ``Polarity``
     - ``0x000``
     - [16]
     - RW
   * - ``ComplEn``
     - ``0x000``
     - [28]
     - RW
   * - ``ComplAnd``
     - ``0x000``
     - [29]
     - RW
   * - ``Enable``
     - ``0x000``
     - [31]
     - RW
   * - ``Delay``
     - ``0x004``
     - [27:0]
     - RW
   * - ``Width``
     - ``0x008``
     - [27:0]
     - RW
   * - ``DelayTap``
     - ``0x00C``
     - [5:0]
     - RW
   * - ``DelayTapReadback``
     - ``0x00C``
     - [21:16]
     - RO

.. _yaml-map-gthrxaligncheck:

GthRxAlignCheck.yaml
--------------------

YAML map: :repo:`yaml/GthRxAlignCheck.yaml`.

Classification: ``drift`` (compared with the PyRogue class and the RTL decode). Register page: :ref:`GthRxAlignCheck registers <register-map-gthrxaligncheck>`.

Includes: none.

Parse status: parses.

Top-level nodes: ``GthRxAlignCheck`` (MMIODev).

.. list-table::
   :header-rows: 1
   :widths: 40 25 15 20

   * - Field
     - Offset
     - Bits
     - Mode
   * - ``PhaseCount[0..39]``
     - ``0x000`` + ``8 bits`` * i
     - [7:0]
     - RO
   * - ``PhaseTarget``
     - ``0x100``
     - [6:0]
     - RW
   * - ``PhaseMask``
     - ``0x100``
     - [14:8]
     - RW
   * - ``ResetLen``
     - ``0x100``
     - [19:16]
     - RW
   * - ``LastPhase``
     - ``0x104``
     - [6:0]
     - RO
   * - ``TxClkFreq``
     - ``0x108``
     - [31:0]
     - RO
   * - ``RxClkFreq``
     - ``0x10C``
     - [31:0]
     - RO

.. _yaml-map-lclstriggerpulse:

LclsTriggerPulse.yaml
---------------------

YAML map: :repo:`yaml/LclsTriggerPulse.yaml`.

Classification: ``drift`` (compared with the PyRogue class and the RTL decode). Register page: :ref:`LclsTriggerPulse registers <register-map-lclstriggerpulse>`.

Includes: none.

Parse status: parses.

Top-level nodes: ``LclsTriggerPulse`` (MMIODev).

.. list-table::
   :header-rows: 1
   :widths: 40 25 15 20

   * - Field
     - Offset
     - Bits
     - Mode
   * - ``OpCodeMask[0..7]``
     - ``0x000`` + ``0x4`` * i
     - [31:0]
     - RW
   * - ``PulseDelay``
     - ``0x020``
     - [31:0]
     - RW
   * - ``PulseWidth``
     - ``0x024``
     - [31:0]
     - RW
   * - ``PulsePolarity``
     - ``0x028``
     - [0]
     - RW

.. _yaml-map-tpg:

TPG.yaml
--------

YAML map: :repo:`yaml/TPG.yaml`.

Classification: ``drift`` (compared with the PyRogue class and the RTL decode). Register page: :ref:`TPG registers <register-map-tpg>`.

Includes:

* ``TPGControl.yaml``
* ``TPGStatus.yaml``
* ``TPGSeqState.yaml``
* ``TPGSeqJump.yaml``
* ``TPGSeqMem.yaml`` (not found beside the map, :issue:`219`)

Parse status: does not parse: ``ScannerError`` at line 69 of the text after the includes are spliced in: mapping values are not allowed here (:issue:`218`).

The fields cannot be listed: the map does not parse.

.. _yaml-map-tpgcontrol:

TPGControl.yaml
---------------

YAML map: :repo:`yaml/TPGControl.yaml`.

Classification: ``drift`` (compared with the PyRogue class and the RTL decode). Register page: :ref:`TPGControl registers <register-map-tpgcontrol>`.

Includes: none.

Parse status: does not parse: ``ScannerError`` at line 58: mapping values are not allowed here (:issue:`218`).

The fields cannot be listed: the map does not parse.

.. _yaml-map-tpgminicore:

TPGMiniCore.yaml
----------------

YAML map: :repo:`yaml/TPGMiniCore.yaml`.

Classification: ``drift`` (compared with the PyRogue class and the RTL decode). Register page: :ref:`TPGMiniCore registers <register-map-tpgminicore>`.

Includes: none.

Parse status: parses.

Top-level nodes: ``TPGMiniCore`` (MMIODev).

.. list-table::
   :header-rows: 1
   :widths: 40 25 15 20

   * - Field
     - Offset
     - Bits
     - Mode
   * - ``TxPolarity``
     - ``0x000``
     - [1]
     - RW
   * - ``TxLoopback``
     - ``0x000``
     - [4:2]
     - RW
   * - ``TxInhibit``
     - ``0x000``
     - [5]
     - RW
   * - ``BaseControl``
     - ``0x004``
     - [15:0]
     - RW
   * - ``PulseIdRd``
     - ``0x008``
     - [63:0]
     - RO
   * - ``TStampRd``
     - ``0x010``
     - [63:0]
     - RO
   * - ``FixedRateDiv[0..9]``
     - ``0x018`` + ``0x4`` * i
     - [31:0]
     - RW
   * - ``RateReload``
     - ``0x040``
     - [0]
     - RW
   * - ``NBeamSeq``
     - ``0x04C``
     - [5:0]
     - RO
   * - ``NControlSeq``
     - ``0x04C``
     - [13:6]
     - RO
   * - ``NArraysBsa``
     - ``0x04C``
     - [21:14]
     - RO
   * - ``SeqAddrLen``
     - ``0x04C``
     - [25:22]
     - RO
   * - ``NAllowSeq``
     - ``0x04C``
     - [31:26]
     - RO
   * - ``BsaCompleteRd``
     - ``0x050``
     - [63:0]
     - RO
   * - ``BsaCompleteWr``
     - ``0x050``
     - [63:0]
     - RW
   * - ``PulseIdWr``
     - ``0x058``
     - [63:0]
     - RW
   * - ``TStampWr``
     - ``0x060``
     - [63:0]
     - RW
   * - ``TxReset``
     - ``0x068``
     - [0]
     - RW
   * - ``CountIntervalReset``
     - ``0x06C``
     - [0]
     - RW
   * - ``PulseIdSet``
     - ``0x070``
     - [0]
     - RW
   * - ``TStampSet``
     - ``0x074``
     - [0]
     - RW
   * - ``Lcls1BsaNumSamples``
     - ``0x078``
     - [11:0]
     - RW
   * - ``Lcls1BsaRate``
     - ``0x078``
     - [14:12]
     - RW
   * - ``Lcls1BsaTimeSlot``
     - ``0x078``
     - [17:15]
     - RW
   * - ``Lcls1BsaSeverity``
     - ``0x078``
     - [19:18]
     - RW
   * - ``Lcls1BsaEdefSlot``
     - ``0x078``
     - [23:20]
     - RW
   * - ``Lcls1BsaNumAvgs``
     - ``0x078``
     - [31:24]
     - RW
   * - ``Lcls1BsaStart``
     - ``0x07C``
     - [31:0]
     - RW
   * - ``BsaActive[0..1]``
     - ``0x1FC`` + ``8 bits`` * i
     - [0]
     - RW
   * - ``BsaRateSelMode[0..1]``
     - ``0x200`` + ``0x10`` * i
     - [1:0]
     - RW
   * - ``BsaFixedRate[0..1]``
     - ``0x200`` + ``0x10`` * i
     - [5:2]
     - RW
   * - ``BsaACRate[0..1]``
     - ``0x200`` + ``0x10`` * i
     - [8:6]
     - RW
   * - ``BsaACTSMask[0..1]``
     - ``0x200`` + ``0x10`` * i
     - [14:9]
     - RW
   * - ``BsaSequenceSelect[0..1]``
     - ``0x200`` + ``0x10`` * i
     - [19:15]
     - RW
   * - ``BsaSequenceBitSelect[0..1]``
     - ``0x200`` + ``0x10`` * i
     - [23:20]
     - RW
   * - ``BsaDestMode[0..1]``
     - ``0x200`` + ``0x10`` * i
     - [25:24]
     - RW
   * - ``BsaDestInclusiveMask[0..1]``
     - ``0x204`` + ``0x10`` * i
     - [15:0]
     - RW
   * - ``BsaDestExclusiveMask[0..1]``
     - ``0x204`` + ``0x10`` * i
     - [31:16]
     - RW
   * - ``BsaNtoAvg[0..1]``
     - ``0x208`` + ``0x10`` * i
     - [12:0]
     - RW
   * - ``BsaMaxSeverity[0..1]``
     - ``0x208`` + ``0x10`` * i
     - [15:14]
     - RW
   * - ``BsaAvgToWr[0..1]``
     - ``0x208`` + ``0x10`` * i
     - [31:16]
     - RW
   * - ``PllCnt``
     - ``0x500``
     - [31:0]
     - RO
   * - ``ClkCnt``
     - ``0x504``
     - [31:0]
     - RO
   * - ``SyncErrCnt``
     - ``0x508``
     - [31:0]
     - RO
   * - ``CountInterval``
     - ``0x50C``
     - [31:0]
     - RW
   * - ``BaseRateCount``
     - ``0x510``
     - [31:0]
     - RO

.. _yaml-map-tpgseqjump:

TPGSeqJump.yaml
---------------

YAML map: :repo:`yaml/TPGSeqJump.yaml`.

Classification: ``drift`` (compared with the PyRogue class and the RTL decode). Register page: :ref:`TPGSeqJump registers <register-map-tpgseqjump>`.

Includes: none.

Parse status: parses.

Top-level nodes: ``TPGSeqJump`` (MMIODev).

.. list-table::
   :header-rows: 1
   :widths: 40 25 15 20

   * - Field
     - Offset
     - Bits
     - Mode
   * - ``StartAddr[0..1023]``
     - ``0x000`` + ``0x4`` * i
     - [11:0]
     - RW
   * - ``Class[0..1023]``
     - ``0x000`` + ``0x4`` * i
     - [11:8]
     - RW
   * - ``StartSync[0..1023]``
     - ``0x000`` + ``0x4`` * i
     - [31:16]
     - RW

.. _yaml-map-tpgseqstate:

TPGSeqState.yaml
----------------

YAML map: :repo:`yaml/TPGSeqState.yaml`.

Classification: ``drift`` (compared with the PyRogue class and the RTL decode). Register page: :ref:`TPGSeqState registers <register-map-tpgseqstate>`.

Includes: none.

Parse status: does not parse: ``ScannerError`` at line 27: mapping values are not allowed here (:issue:`218`).

The fields cannot be listed: the map does not parse.

.. _yaml-map-tpgstatus:

TPGStatus.yaml
--------------

YAML map: :repo:`yaml/TPGStatus.yaml`.

Classification: ``drift`` (compared with the PyRogue class and the RTL decode). Register page: :ref:`TPGStatus registers <register-map-tpgstatus>`.

Includes: none.

Parse status: parses.

Top-level nodes: ``TPGStatus`` (MMIODev).

.. list-table::
   :header-rows: 1
   :widths: 40 25 15 20

   * - Field
     - Offset
     - Bits
     - Mode
   * - ``BsaStat[0..63]``
     - ``0x000`` + ``0x4`` * i
     - [31:0]
     - RO
   * - ``CountPLL``
     - ``0x100``
     - [31:0]
     - RO
   * - ``Count186M``
     - ``0x104``
     - [31:0]
     - RO
   * - ``CountSyncE``
     - ``0x108``
     - [31:0]
     - RO
   * - ``CountIntv``
     - ``0x10C``
     - [31:0]
     - RW
   * - ``CountBRT``
     - ``0x110``
     - [31:0]
     - RO
   * - ``CountTrig[0..11]``
     - ``0x114`` + ``0x0`` * i
     - [31:0]
     - RO
   * - ``CountSeq[0..63]``
     - ``0x144`` + ``16 bits`` * i
     - [31:0]
     - RO
   * - ``CountRxClks``
     - ``0x248``
     - [31:0]
     - RW
   * - ``CountRxDV``
     - ``0x24C``
     - [31:0]
     - RW

.. _yaml-map-timingframerx:

TimingFrameRx.yaml
------------------

YAML map: :repo:`yaml/TimingFrameRx.yaml`.

Classification: ``drift`` (compared with the PyRogue class and the RTL decode). Register page: :ref:`TimingFrameRx registers <register-map-timingframerx>`.

Includes: none.

Parse status: parses.

Top-level nodes: ``TimingFrameRx`` (MMIODev).

.. list-table::
   :header-rows: 1
   :widths: 40 25 15 20

   * - Field
     - Offset
     - Bits
     - Mode
   * - ``sofCount``
     - ``0x000``
     - [31:0]
     - RO
   * - ``eofCount``
     - ``0x004``
     - [31:0]
     - RO
   * - ``FidCount``
     - ``0x008``
     - [31:0]
     - RO
   * - ``CrcErrCount``
     - ``0x00C``
     - [31:0]
     - RO
   * - ``RxClkCount``
     - ``0x010``
     - [31:0]
     - RO
   * - ``RxRstCount``
     - ``0x014``
     - [31:0]
     - RO
   * - ``RxDecErrCount``
     - ``0x018``
     - [31:0]
     - RO
   * - ``RxDspErrCount``
     - ``0x01C``
     - [31:0]
     - RO
   * - ``RxCountReset``
     - ``0x020``
     - [0]
     - RW
   * - ``RxLinkUp``
     - ``0x020``
     - [1]
     - RO
   * - ``RxPolarity``
     - ``0x020``
     - [2]
     - RW
   * - ``RxReset``
     - ``0x020``
     - [3]
     - RW
   * - ``ClkSel``
     - ``0x020``
     - [4]
     - RW
   * - ``RxDown``
     - ``0x020``
     - [5]
     - RW
   * - ``BypassRst``
     - ``0x020``
     - [6]
     - RW
   * - ``RxPLLReset``
     - ``0x020``
     - [7]
     - RW
   * - ``VersionErr``
     - ``0x020``
     - [8]
     - RO
   * - ``ModeSel``
     - ``0x020``
     - [9]
     - RW
   * - ``ModeSelEn``
     - ``0x020``
     - [10]
     - RW
   * - ``MsgNoDelay``
     - ``0x020``
     - [24]
     - RW
   * - ``MsgDelay``
     - ``0x024``
     - [19:0]
     - RW
   * - ``MsgDelayRst``
     - ``0x024``
     - [31]
     - RW
   * - ``TxClkCount``
     - ``0x028``
     - [31:0]
     - RO
   * - ``BypassDoneCount``
     - ``0x02C``
     - [15:0]
     - RO
   * - ``BypassResetCount``
     - ``0x02C``
     - [31:16]
     - RO
   * - ``FrameVersion``
     - ``0x030``
     - [31:0]
     - RO
