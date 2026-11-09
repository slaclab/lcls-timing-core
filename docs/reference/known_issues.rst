Known issues
============

Every known defect and open question of the library on one page, with the test or baseline entry that reproduces it and the reference page that shows it. The page is generated from the sources by ``python -m tests.common.gen_docs``: a test fails when an issue appears in the repository and not here, or here and not in the repository.

A **gated test** is skipped unless the environment variable ``RUN_KNOWN_ISSUE_TESTS=1`` is set. The run ``RUN_KNOWN_ISSUE_TESTS=1 python -m pytest --expect-known-issues -rxX tests/<leg>`` selects only the gated tests and expects each one to fail, so an issue that still reproduces is reported as XFAIL and one that no longer reproduces is reported as XPASS, which fails the run until its skip is removed. A **GHDL baseline** records the exact message GHDL prints for a file it cannot analyze; the regression fails when the message changes or disappears. The **register drift allowlist** lists each difference between the RTL decode, the PyRogue variables, and the YAML map that is known and linked, and a test fails when an entry no longer differs. The header issues, the unloaded sources, and the YAML baselines work the same way: each entry names its issue and the regression fails when the entry goes stale.

Issue 207
---------

Tracker: :issue:`207`.

.. list-table::
   :header-rows: 1
   :widths: 40 40 20

   * - Source
     - Detail
     - Shown on
   * - gated test: ``tests/lcls2_core/test_TimingSerialDelay.py::test_TimingSerialDelay_known_issue_empty_frame``
     - TimingSerialDelay never reads stream_i.ready, so an empty frame merges into the next frame
     - :ref:`TimingSerialDelay <entity-lcls-ii-core-rtl-timingserialdelay-vhd>`

Issue 208
---------

Tracker: :issue:`208`.

.. list-table::
   :header-rows: 1
   :widths: 40 40 20

   * - Source
     - Detail
     - Shown on
   * - gated test: ``tests/lcls2_core/test_TimingMsgToAxiStream.py::test_TimingMsgToAxiStream_known_issue_framing``
     - TimingMsgToAxiStream never ends a frame
     - :ref:`TimingMsgToAxiStream <entity-lcls-ii-core-rtl-timingmsgtoaxistream-vhd>`

Issue 209
---------

Tracker: :issue:`209`.

.. list-table::
   :header-rows: 1
   :widths: 40 40 20

   * - Source
     - Detail
     - Shown on
   * - gated test: ``tests/lcls2_core/test_BsaControl.py::test_BsaControl_known_issue_rate_field_comment``
     - TPGPkg rateSel comment disagrees with the sequence-mode field mapping
     - :ref:`BsaControl <entity-lcls-ii-core-rtl-bsacontrolv2-vhd>`

Issue 210
---------

Tracker: :issue:`210`.

.. list-table::
   :header-rows: 1
   :widths: 40 40 20

   * - Source
     - Detail
     - Shown on
   * - gated test: ``tests/lcls2_core/test_GthRxAlignCheck.py::test_GthRxAlignCheck_known_issue_sample_index``
     - GthRxAlignCheck indexes a 40-entry histogram with a 7-bit DRP value
     - :ref:`GthRxAlignCheck <entity-lcls-ii-core-rtl-gthrxaligncheck-vhd>`

Issue 211
---------

Tracker: :issue:`211`.

.. list-table::
   :header-rows: 1
   :widths: 40 40 20

   * - Source
     - Detail
     - Shown on
   * - gated test: ``tests/lcls2_core/test_TimingFrameRx.py::test_TimingFrameRx_known_issue_valid_on_strobe``
     - Open question: TimingFrameRx timingMessageValid and staData(4) lag the strobe by one cycle
     - :ref:`TimingFrameRx <entity-lcls-ii-core-rtl-timingframerx-vhd>`

Issue 212
---------

Tracker: :issue:`212`.

.. list-table::
   :header-rows: 1
   :widths: 40 40 20

   * - Source
     - Detail
     - Shown on
   * - gated test: ``tests/lcls2_evr/test_EvrV2Trigger.py::test_EvrV2Trigger_known_issue_channel_index``
     - EvrV2Trigger indexes arm with a channel at or above CHANNELS_C and GHDL aborts
     - :ref:`EvrV2Trigger <entity-lcls-ii-evr-rtl-evrv2trigger-vhd>`

Issue 213
---------

Tracker: :issue:`213`.

.. list-table::
   :header-rows: 1
   :widths: 40 40 20

   * - Source
     - Detail
     - Shown on
   * - gated test: ``tests/lcls2_evr/test_EvrV2EventSelect.py::test_EvrV2EventSelect_known_issue_control_index``
     - EvrV2EventSelect indexes the 18-word control array with rateSel(8:4) up to 31 and GHDL aborts at 18
     - :ref:`EvrV2EventSelect <entity-lcls-ii-evr-rtl-evrv2eventselect-vhd>`

Issue 214
---------

Tracker: :issue:`214`.

.. list-table::
   :header-rows: 1
   :widths: 40 40 20

   * - Source
     - Detail
     - Shown on
   * - gated test: ``tests/lcls2_evr/test_EvrV2TrigReg.py::test_EvrV2TrigReg_known_issue_compl_bits``
     - EvrV2TriggerReg.py places ComplEn and ComplAnd one bit above the RTL decode
     - :ref:`EvrV2TrigReg <entity-lcls-ii-evr-rtl-evrv2trigreg-vhd>`
   * - register drift allowlist: ``EvrV2CoreTriggers``
     - ``EvrV2TriggerReg.ComplAnd`` (bitOffset); ``EvrV2TriggerReg.ComplEn`` (bitOffset)
     - :ref:`EvrV2CoreTriggers <register-map-evrv2coretriggers>`
   * - register drift allowlist: ``EvrV2TriggerReg``
     - ``ComplAnd`` (bitOffset); ``ComplEn`` (bitOffset)
     - :ref:`EvrV2TriggerReg <register-map-evrv2triggerreg>`

Issue 215
---------

Tracker: :issue:`215`.

.. list-table::
   :header-rows: 1
   :widths: 40 40 20

   * - Source
     - Detail
     - Shown on
   * - gated test: ``tests/lcls2_evr/test_EvrV2Axi.py::test_EvrV2Axi_known_issue_channel_width``
     - EvrV2Core.py channel variables disagree with the EvrV2Axi decode in width and channel count
     - :ref:`EvrV2Axi <entity-lcls-ii-evr-rtl-evrv2axi-vhd>`
   * - gated test: ``tests/lcls2_evr/test_EvrV2ChannelReg.py::test_EvrV2ChannelReg_known_issue_field_width``
     - EvrV2ChannelReg.py covers 18 of the 19 RTL destSel bits
     - :ref:`EvrV2ChannelReg <entity-lcls-ii-evr-rtl-evrv2channelreg-vhd>`
   * - register drift allowlist: ``EvrV2ChannelReg``
     - ``DestSel`` (bitSize); ``DestType`` (missing-in-vhdl, missing-in-yaml); ``RateSel`` (bitSize); ``RateType`` (missing-in-vhdl, missing-in-yaml)
     - :ref:`EvrV2ChannelReg <register-map-evrv2channelreg>`
   * - register drift allowlist: ``EvrV2Core``
     - ``ChannelBsaSetup`` (bitSize); ``ChannelDestSel`` (bitSize); ``ChannelEnable`` (missing-in-python); ``ChannelRateSel`` (missing-in-python)
     - :ref:`EvrV2Core <register-map-evrv2core>`
   * - register drift allowlist: ``EvrV2CoreTriggers``
     - ``EvrV2ChannelReg.DestSel`` (bitSize); ``EvrV2ChannelReg.DestType`` (missing-in-yaml); ``EvrV2ChannelReg.RateSel`` (bitSize); ``EvrV2ChannelReg.RateType`` (missing-in-yaml)
     - :ref:`EvrV2CoreTriggers <register-map-evrv2coretriggers>`

Issue 216
---------

Tracker: :issue:`216`.

.. list-table::
   :header-rows: 1
   :widths: 40 40 20

   * - Source
     - Detail
     - Shown on
   * - gated test: ``tests/lcls1_evr/test_EvrV1DbusDecode.py::test_EvrV1DbusDecode_known_issue_unpatched``
     - EvrV1DbusDecode.v has an unsized constant in a concatenation that Icarus rejects
     - :ref:`EvrV1DbusDecode <entity-lcls-i-evr-evrv1dbusdecode-v>`

Issue 217
---------

Tracker: :issue:`217`.

.. list-table::
   :header-rows: 1
   :widths: 40 40 20

   * - Source
     - Detail
     - Shown on
   * - gated test: ``tests/lcls2_evr/test_EvrV2CorePulseGen.py::test_EvrV2CorePulseGen_known_issue_irq_request``
     - EvrV2CorePulseGen leaves irqReq undriven so it reads unresolved after reset
     - :ref:`EvrV2CorePulseGen <entity-lcls-ii-evr-rtl-evrv2corepulsegen-vhd>`
   * - gated test: ``tests/lcls2_evr/test_EvrV2CorePulseGen.py::test_EvrV2CorePulseGen_known_issue_lcls1_strobe``
     - EvrV2CorePulseGen with evrModeSel low aborts the simulator at the first timing strobe because the event message assignment is 32 bits narrower than its target
     - :ref:`EvrV2CorePulseGen <entity-lcls-ii-evr-rtl-evrv2corepulsegen-vhd>`
   * - gated test: ``tests/lcls2_evr/test_EvrV2Trigger.py::test_EvrV2Trigger_known_issue_polarity_idle``
     - EvrV2Trigger with polarity 0 idles low until the first pulse completes
     - :ref:`EvrV2Trigger <entity-lcls-ii-evr-rtl-evrv2trigger-vhd>`
   * - gated test: ``tests/rogue/test_EvrV1Reg.py::test_EvrV1Reg_known_issue_overlap``
     - EvrV1Reg.py declares IrqFlagWr and IrqFlagRd on the same bits of 0x08 without overlapEn, so Rogue rejects the tree
     - :ref:`EvrV1Reg <api-evrv1reg>`
   * - register drift allowlist: ``EvrV1Reg``
     - ``IrqFlagRd`` (bitSize, missing-in-yaml); ``IrqFlagWr`` (mode)
     - :ref:`EvrV1Reg <register-map-evrv1reg>`
   * - register drift allowlist: ``EvrV2Core``
     - ``ChannelEventCnt`` (mode); ``GlobalEventCnt`` (mode); ``TriggerDelay`` (offset); ``TriggerWidth`` (missing-in-python)
     - :ref:`EvrV2Core <register-map-evrv2core>`

Issue 218
---------

Tracker: :issue:`218`.

.. list-table::
   :header-rows: 1
   :widths: 40 40 20

   * - Source
     - Detail
     - Shown on
   * - gated test: ``tests/common/test_yaml_maps.py::test_yaml_known_issue_every_file_parses``
     - TPG.yaml, TPGControl.yaml, and TPGSeqState.yaml do not parse
     - :doc:`/reference/yaml_maps`
   * - register drift allowlist: ``TPG``
     - ``<yaml>`` (missing-in-yaml)
     - :ref:`TPG <register-map-tpg>`
   * - register drift allowlist: ``TPGControl``
     - ``<yaml>`` (missing-in-yaml)
     - :ref:`TPGControl <register-map-tpgcontrol>`
   * - register drift allowlist: ``TPGSeqState``
     - ``<yaml>`` (missing-in-yaml)
     - :ref:`TPGSeqState <register-map-tpgseqstate>`
   * - YAML defect: ``TPG.yaml``
     - TPG.yaml does not parse: ScannerError at line 69, mapping values are not allowed here
     - :ref:`TPG.yaml <yaml-map-tpg>`
   * - YAML defect: ``TPGControl.yaml``
     - TPGControl.yaml does not parse: ScannerError at line 58, mapping values are not allowed here
     - :ref:`TPGControl.yaml <yaml-map-tpgcontrol>`
   * - YAML defect: ``TPGSeqState.yaml``
     - TPGSeqState.yaml does not parse: ScannerError at line 27, mapping values are not allowed here
     - :ref:`TPGSeqState.yaml <yaml-map-tpgseqstate>`

Issue 219
---------

Tracker: :issue:`219`.

.. list-table::
   :header-rows: 1
   :widths: 40 40 20

   * - Source
     - Detail
     - Shown on
   * - gated test: ``tests/common/test_yaml_maps.py::test_yaml_known_issue_tpgseqmem_include``
     - TPG.yaml includes TPGSeqMem.yaml, which does not exist in yaml/
     - :doc:`/reference/yaml_maps`
   * - YAML missing include: ``TPG.yaml``
     - TPG.yaml includes TPGSeqMem.yaml, which does not exist in yaml/
     - :ref:`TPG.yaml <yaml-map-tpg>`

Issue 220
---------

Tracker: :issue:`220`.

.. list-table::
   :header-rows: 1
   :widths: 40 40 20

   * - Source
     - Detail
     - Shown on
   * - gated test: ``tests/rogue/test_TPGSeqJump.py::test_TPGSeqJump_known_issue_overlap``
     - TPGSeqJump.py declares Class at byte 1 bit 0, overlapping bits 8 to 11 of StartAddr, so Rogue rejects the tree
     - :ref:`TPGSeqJump <api-tpgseqjump>`

Issue 221
---------

Tracker: :issue:`221`.

.. list-table::
   :header-rows: 1
   :widths: 40 40 20

   * - Source
     - Detail
     - Shown on
   * - gated test: ``tests/rogue/test_TPGSeqState.py::test_TPGSeqState_known_issue_overlap``
     - TPGSeqState.py declares SeqCondACount, SeqCondBCount, SeqCondCCount, and SeqCondDCount at the same bit of byte 4, so Rogue rejects the tree
     - :ref:`TPGSeqState <api-tpgseqstate>`

Issue 222
---------

Tracker: :issue:`222`.

.. list-table::
   :header-rows: 1
   :widths: 40 40 20

   * - Source
     - Detail
     - Shown on
   * - gated test: ``tests/rogue/test_TPGMiniCore.py::test_TPGMiniCore_known_issue_bsa_avg_to_wr_stride``
     - TPGMiniCore.py declares BsaAvgToWr with a stride of 8 where TPGMiniReg decodes 16 bytes per sequence
     - :ref:`TPGMiniCore <api-tpgminicore>`
   * - register drift allowlist: ``TPGMiniCore``
     - ``BsaAvgToWr`` (offset)
     - :ref:`TPGMiniCore <register-map-tpgminicore>`

Issue 223
---------

Tracker: :issue:`223`.

.. list-table::
   :header-rows: 1
   :widths: 40 40 20

   * - Source
     - Detail
     - Shown on
   * - gated test: ``tests/rogue/test_TPGMiniCore.py::test_TPGMiniCore_known_issue_narraysbsa_32``
     - TPGMiniCore.py declares BsaActive with a byte stride where TPGMiniReg decodes one bit per sequence, so NARRAYSBSA above 4 is rejected
     - :ref:`TPGMiniCore <api-tpgminicore>`
   * - register drift allowlist: ``TPGMiniCore``
     - ``BsaActive`` (bitOffset)
     - :ref:`TPGMiniCore <register-map-tpgminicore>`

Issue 224
---------

Tracker: :issue:`224`.

.. list-table::
   :header-rows: 1
   :widths: 40 40 20

   * - Source
     - Detail
     - Shown on
   * - register drift allowlist: ``GthRxAlignCheck``
     - ``PhaseCount`` (bitSize, missing-in-vhdl, missing-in-yaml, offset)
     - :ref:`GthRxAlignCheck <register-map-gthrxaligncheck>`

Issue 225
---------

Tracker: :issue:`225`.

.. list-table::
   :header-rows: 1
   :widths: 40 40 20

   * - Source
     - Detail
     - Shown on
   * - register drift allowlist: ``TPGMiniCore``
     - ``FixedRateDiv`` (bitSize)
     - :ref:`TPGMiniCore <register-map-tpgminicore>`

Issue 226
---------

Tracker: :issue:`226`.

.. list-table::
   :header-rows: 1
   :widths: 40 40 20

   * - Source
     - Detail
     - Shown on
   * - register drift allowlist: ``EvrV1Reg``
     - ``IntEventCount`` (bitSize); ``IntEventEn`` (bitSize)
     - :ref:`EvrV1Reg <register-map-evrv1reg>`

Issue 227
---------

Tracker: :issue:`227`.

.. list-table::
   :header-rows: 1
   :widths: 40 40 20

   * - Source
     - Detail
     - Shown on
   * - register drift allowlist: ``EvrV1Reg``
     - ``OutputMap`` (bitOffset, offset)
     - :ref:`EvrV1Reg <register-map-evrv1reg>`

Issue 228
---------

Tracker: :issue:`228`.

.. list-table::
   :header-rows: 1
   :widths: 40 40 20

   * - Source
     - Detail
     - Shown on
   * - gated test: ``tests/rogue/test_TPG.py::test_TPG_known_issue_overlap``
     - TPG.py inherits the TPGStatus CountSeq overlap (and the TPGSeqJump and TPGSeqState overlaps of issues 220 and 221), and also adds TPGStatus and TPGSeqJump both at 0x400, so Rogue rejects the tree
     - :ref:`TPG <api-tpg>`
   * - gated test: ``tests/rogue/test_TPGStatus.py::test_TPGStatus_known_issue_overlap``
     - TPGStatus.py declares CountSeq with a stride of 2 bytes for 32 bit counters, so neighbouring elements overlap and Rogue rejects the tree
     - :ref:`TPGStatus <api-tpgstatus>`
   * - register drift allowlist: ``EvrV1Reg``
     - ``DataBufferControl`` (missing-in-python, missing-in-yaml); ``MapRam1`` (missing-in-python, missing-in-vhdl); ``MapRam2`` (missing-in-python, missing-in-vhdl); ``Pulse00`` (offset); ``Pulse01`` (offset); ``Pulse02`` (offset); ``Pulse03`` (offset); ``Pulse04`` (offset); ``Pulse05`` (offset); ``Pulse06`` (offset); ``Pulse07`` (offset); ``Pulse08`` (offset); ``Pulse09`` (offset); ``Pulse10`` (offset); ``Pulse11`` (offset); ``TimestampFifo`` (missing-in-python, missing-in-yaml)
     - :ref:`EvrV1Reg <register-map-evrv1reg>`
   * - register drift allowlist: ``EvrV2Core``
     - ``LinkAddr`` (missing-in-python, missing-in-vhdl)
     - :ref:`EvrV2Core <register-map-evrv2core>`
   * - register drift allowlist: ``GthRxAlignCheck``
     - ``LastPhase`` (bitSize, mode); ``PhaseCount`` (mode)
     - :ref:`GthRxAlignCheck <register-map-gthrxaligncheck>`
   * - register drift allowlist: ``TPGMiniCore``
     - ``BsaCompleteWr`` (mode); ``CountIntervalReset`` (mode); ``Lcls1BsaStart`` (mode); ``PulseIdSet`` (mode); ``PulseIdWr`` (mode); ``RateReload`` (mode); ``TStampSet`` (mode); ``TStampWr`` (mode); ``TxReset`` (mode); ``bsastatus`` (missing-in-python, missing-in-yaml)
     - :ref:`TPGMiniCore <register-map-tpgminicore>`
   * - register drift allowlist: ``TPGStatus``
     - ``CountTrig`` (offset)
     - :ref:`TPGStatus <register-map-tpgstatus>`
   * - register drift allowlist: ``TimingFrameRx``
     - ``C_RxReset`` (mode); ``ClearRxCounters`` (mode); ``FrameVersion`` (missing-in-python); ``MsgDelayRst`` (missing-in-python); ``MsgNoDelay`` (missing-in-python); ``RxPllReset`` (mode); ``VersionErr`` (missing-in-python); ``timingTSEvCntGray_o`` (missing-in-python, missing-in-yaml)
     - :ref:`TimingFrameRx <register-map-timingframerx>`

Issue 229
---------

Tracker: :issue:`229`.

.. list-table::
   :header-rows: 1
   :widths: 40 40 20

   * - Source
     - Detail
     - Shown on
   * - gated test: ``tests/common/test_release_tooling.py::test_ruckus_known_issue_surf_locks_agree``
     - the root ruckus.tcl requires surf 2.53.0 while LCLS-II/gtx7/ruckus.tcl requires surf 2.74.0
     - :doc:`/reference/families`

Issue 232
---------

Tracker: :issue:`232`.

.. list-table::
   :header-rows: 1
   :widths: 40 40 20

   * - Source
     - Detail
     - Shown on
   * - gated test: ``tests/common/test_release_tooling.py::test_setup_known_issue_imports_on_python_312``
     - setup.py imports distutils, which Python 3.12 removed
     - :doc:`/how-to/release_flow`

Issue 233
---------

Tracker: :issue:`233`.

.. list-table::
   :header-rows: 1
   :widths: 40 40 20

   * - Source
     - Detail
     - Shown on
   * - gated test: ``tests/common/test_release_tooling.py::test_setup_known_issue_build_leaves_the_package_unchanged``
     - setup.py appends __version__ to the tracked package __init__.py on every run
     - :doc:`/how-to/release_flow`

Issue 234
---------

Tracker: :issue:`234`.

.. list-table::
   :header-rows: 1
   :widths: 40 40 20

   * - Source
     - Detail
     - Shown on
   * - GHDL baseline: ``timingcore``
     - GHDL reports ``not locally static``
     - :ref:`TimingCore <entity-lcls-ii-core-rtl-timingcore-vhd>`
   * - GHDL baseline: ``tpgminicore``
     - GHDL reports ``not locally static``
     - :ref:`TPGMiniCore <entity-lcls-ii-core-rtl-tpgminicore-vhd>`
   * - GHDL baseline: ``tpgminireg``
     - GHDL reports ``not locally static``
     - :ref:`TPGMiniReg <entity-lcls-ii-core-rtl-tpgminireg-vhd>`

Issue 235
---------

Tracker: :issue:`235`.

.. list-table::
   :header-rows: 1
   :widths: 40 40 20

   * - Source
     - Detail
     - Shown on
   * - GHDL baseline: ``evrv2module``
     - GHDL reports ``must be locally static``
     - :ref:`EvrV2Module <entity-lcls-ii-evr-rtl-evrv2module-vhd>`

Issue 236
---------

Tracker: :issue:`236`.

.. list-table::
   :header-rows: 1
   :widths: 40 40 20

   * - Source
     - Detail
     - Shown on
   * - GHDL baseline: ``evrv1coreisrctrl``
     - GHDL reports ``string length does not match``
     - :ref:`EvrV1CoreIsrCtrl <entity-lcls-i-evr-evrv1coreisrctrl-vhd>`

Issue 237
---------

Tracker: :issue:`237`.

.. list-table::
   :header-rows: 1
   :widths: 40 40 20

   * - Source
     - Detail
     - Shown on
   * - GHDL baseline: ``evrv2_tb``
     - GHDL reports ``no declaration for "exptbustype"``
     - :ref:`EvrV2_tb <entity-lcls-ii-evr-tb-evrv2-tb-vhd>`

Issue 238
---------

Tracker: :issue:`238`.

.. list-table::
   :header-rows: 1
   :widths: 40 40 20

   * - Source
     - Detail
     - Shown on
   * - gated test: ``tests/common/test_unloaded_sources.py::test_unloaded_sources_known_issue_every_rtl_file_is_loaded``
     - eight RTL files are loaded by no ruckus.tcl, and BsaControl.vhd declares the same entity as the loaded BsaControlv2.vhd
     - :doc:`/reference/entities/core`
   * - GHDL baseline: ``timinggthwrapper``
     - GHDL reports ``no declaration for "ieee"``
     - :ref:`TimingGthWrapper <entity-lcls-ii-core-rtl-timinggthwrapper-vhd>`
   * - unloaded sources: ``LCLS-II/core/rtl/BsaControl.vhd``
     - no ruckus.tcl loads the file
     - :ref:`BsaControl <entity-lcls-ii-core-rtl-bsacontrol-vhd>`
   * - unloaded sources: ``LCLS-II/core/rtl/ClockTime_186MHz.vhd``
     - no ruckus.tcl loads the file
     - :ref:`ClockTime_186MHz <entity-lcls-ii-core-rtl-clocktime-186mhz-vhd>`
   * - unloaded sources: ``LCLS-II/core/rtl/TPFifo.vhd``
     - no ruckus.tcl loads the file
     - :ref:`TPFifo <entity-lcls-ii-core-rtl-tpfifo-vhd>`
   * - unloaded sources: ``LCLS-II/core/rtl/TPGMiniEdefTb.vhd``
     - no ruckus.tcl loads the file
     - :ref:`TPGMiniEdefTb <entity-lcls-ii-core-rtl-tpgminiedeftb-vhd>`
   * - unloaded sources: ``LCLS-II/core/rtl/TPGNotify.vhd``
     - no ruckus.tcl loads the file
     - :ref:`TPGNotify <entity-lcls-ii-core-rtl-tpgnotify-vhd>`
   * - unloaded sources: ``LCLS-II/core/rtl/TimingGthWrapper.vhd``
     - no ruckus.tcl loads the file
     - :ref:`TimingGthWrapper <entity-lcls-ii-core-rtl-timinggthwrapper-vhd>`
   * - unloaded sources: ``LCLS-II/core/rtl/default/TimingExtnPkg.vhd``
     - no ruckus.tcl loads the file
     - :ref:`TimingExtnPkg <package-timingextnpkg>`
   * - unloaded sources: ``LCLS-II/core/tb/TimingSerialDelay_tb.vhd``
     - no ruckus.tcl loads the file
     - :ref:`TimingSerialDelayTb <entity-lcls-ii-core-tb-timingserialdelay-tb-vhd>`

Issue 239
---------

Tracker: :issue:`239`.

.. list-table::
   :header-rows: 1
   :widths: 40 40 20

   * - Source
     - Detail
     - Shown on
   * - header issues: ``LCLS-I/evr/EvrV1Core.vhd``
     - The banner description field is empty
     - :ref:`EvrV1Core <entity-lcls-i-evr-evrv1core-vhd>`
   * - header issues: ``LCLS-I/evr/EvrV1CoreIsrCtrl.vhd``
     - The banner description field is empty
     - :ref:`EvrV1CoreIsrCtrl <entity-lcls-i-evr-evrv1coreisrctrl-vhd>`
   * - header issues: ``LCLS-I/evr/EvrV1Databuff.vhd``
     - The banner description field is empty
     - :ref:`EvrV1Databuff <entity-lcls-i-evr-evrv1databuff-vhd>`
   * - header issues: ``LCLS-I/evr/EvrV1DbusDecode.v``
     - The file has no banner description field
     - :ref:`EvrV1DbusDecode <entity-lcls-i-evr-evrv1dbusdecode-v>`
   * - header issues: ``LCLS-I/evr/EvrV1EventRAM256x32.vhd``
     - The banner description field is empty
     - :ref:`EvrV1EventRAM256x32 <entity-lcls-i-evr-evrv1eventram256x32-vhd>`
   * - header issues: ``LCLS-I/evr/EvrV1EventReceiver.vhd``
     - The banner description field is empty
     - :ref:`EvrV1EventReceiver <entity-lcls-i-evr-evrv1eventreceiver-vhd>`
   * - header issues: ``LCLS-I/evr/EvrV1EventReceiverChannel.v``
     - The file has no banner description field
     - :ref:`EvrV1EventReceiverChannel <entity-lcls-i-evr-evrv1eventreceiverchannel-v>`
   * - header issues: ``LCLS-I/evr/EvrV1HeartBeat.vhd``
     - The banner description contradicts what the file does
     - :ref:`EvrV1HeartBeat <entity-lcls-i-evr-evrv1heartbeat-vhd>`
   * - header issues: ``LCLS-I/evr/EvrV1Pkg.vhd``
     - The banner description field is empty
     - :ref:`EvrV1Pkg <package-evrv1pkg>`
   * - header issues: ``LCLS-I/evr/EvrV1Reg.vhd``
     - The banner description field is empty
     - :ref:`EvrV1Reg <entity-lcls-i-evr-evrv1reg-vhd>`
   * - header issues: ``LCLS-I/evr/EvrV1TimeStampFIFO.vhd``
     - The banner description field is empty
     - :ref:`EvrV1TimeStampFIFO <entity-lcls-i-evr-evrv1timestampfifo-vhd>`
   * - header issues: ``LCLS-I/evr/EvrV1TimeStampGenerator.v``
     - The file has no banner description field
     - :ref:`EvrV1TimeStampGenerator <entity-lcls-i-evr-evrv1timestampgenerator-v>`
   * - header issues: ``LCLS-I/evr/EvrV1TimeofDayReceiver.v``
     - The file has no banner description field
     - :ref:`EvrV1TimeofDayReceiver <entity-lcls-i-evr-evrv1timeofdayreceiver-v>`
   * - header issues: ``LCLS-II/core/rtl/CtrControl.vhd``
     - The banner description contradicts what the file does
     - :ref:`CtrControl <entity-lcls-ii-core-rtl-ctrcontrol-vhd>`
   * - header issues: ``LCLS-II/core/rtl/EthTimingModule.vhd``
     - The banner description field is empty
     - :ref:`EthTimingModule <entity-lcls-ii-core-rtl-ethtimingmodule-vhd>`
   * - header issues: ``LCLS-II/core/rtl/TPGMini.vhd``
     - The banner description field is empty
     - :ref:`TPGMini <entity-lcls-ii-core-rtl-tpgmini-vhd>`
   * - header issues: ``LCLS-II/core/rtl/TPGMiniCore.vhd``
     - The banner description field is empty
     - :ref:`TPGMiniCore <entity-lcls-ii-core-rtl-tpgminicore-vhd>`
   * - header issues: ``LCLS-II/core/rtl/TPGMiniEdef.vhd``
     - The banner description field is empty
     - :ref:`TPGMiniEdef <entity-lcls-ii-core-rtl-tpgminiedef-vhd>`
   * - header issues: ``LCLS-II/core/rtl/TPGMiniEdefPkg.vhd``
     - The banner description field is empty
     - :ref:`TPGMiniEdefPkg <package-tpgminiedefpkg>`
   * - header issues: ``LCLS-II/core/rtl/TPGMiniEdefTb.vhd``
     - The banner description field is empty
     - :ref:`TPGMiniEdefTb <entity-lcls-ii-core-rtl-tpgminiedeftb-vhd>`
   * - header issues: ``LCLS-II/core/rtl/TPGMiniReg.vhd``
     - The banner description field is empty
     - :ref:`TPGMiniReg <entity-lcls-ii-core-rtl-tpgminireg-vhd>`
   * - header issues: ``LCLS-II/core/rtl/TPGNotify.vhd``
     - The banner description field is empty
     - :ref:`TPGNotify <entity-lcls-ii-core-rtl-tpgnotify-vhd>`
   * - header issues: ``LCLS-II/core/rtl/TimingCore.vhd``
     - The banner description field is empty
     - :ref:`TimingCore <entity-lcls-ii-core-rtl-timingcore-vhd>`
   * - header issues: ``LCLS-II/core/rtl/TimingDeserializer.vhd``
     - The banner description contradicts what the file does
     - :ref:`TimingDeserializer <entity-lcls-ii-core-rtl-timingdeserializer-vhd>`
   * - header issues: ``LCLS-II/core/rtl/TimingFrameRx.vhd``
     - The banner description field is empty
     - :ref:`TimingFrameRx <entity-lcls-ii-core-rtl-timingframerx-vhd>`
   * - header issues: ``LCLS-II/core/rtl/TimingGthWrapper.vhd``
     - The banner description field is empty
     - :ref:`TimingGthWrapper <entity-lcls-ii-core-rtl-timinggthwrapper-vhd>`
   * - header issues: ``LCLS-II/core/rtl/TimingMsgAxiRingBuffer.vhd``
     - The banner description field is empty
     - :ref:`TimingMsgAxiRingBuffer <entity-lcls-ii-core-rtl-timingmsgaxiringbuffer-vhd>`
   * - header issues: ``LCLS-II/core/rtl/TimingMsgDelay.vhd``
     - The banner description field is empty
     - :ref:`TimingMsgDelay <entity-lcls-ii-core-rtl-timingmsgdelay-vhd>`
   * - header issues: ``LCLS-II/core/rtl/TimingPkg.vhd``
     - The banner description field is empty
     - :ref:`TimingPkg <package-timingpkg>`
   * - header issues: ``LCLS-II/core/rtl/TimingStreamTx.vhd``
     - The banner description contradicts what the file does
     - :ref:`TimingStreamTx <entity-lcls-ii-core-rtl-timingstreamtx-vhd>`
   * - header issues: ``LCLS-II/core/rtl/default/TimingExtnPkg.vhd``
     - The banner description field is empty
     - :ref:`TimingExtnPkg <package-timingextnpkg>`
   * - header issues: ``LCLS-II/evr/rtl/EvrV2Axi.vhd``
     - The banner description field is empty
     - :ref:`EvrV2Axi <entity-lcls-ii-evr-rtl-evrv2axi-vhd>`
   * - header issues: ``LCLS-II/evr/rtl/EvrV2Cache.vhd``
     - The banner description field is empty
     - :ref:`EvrV2Cache <entity-lcls-ii-evr-rtl-evrv2cache-vhd>`
   * - header issues: ``LCLS-II/evr/rtl/EvrV2ChannelReg.vhd``
     - The banner description field is empty
     - :ref:`EvrV2ChannelReg <entity-lcls-ii-evr-rtl-evrv2channelreg-vhd>`
   * - header issues: ``LCLS-II/evr/rtl/EvrV2CoreChannels.vhd``
     - The banner description field is empty
     - :ref:`EvrV2CoreChannels <entity-lcls-ii-evr-rtl-evrv2corechannels-vhd>`
   * - header issues: ``LCLS-II/evr/rtl/EvrV2CoreTriggers.vhd``
     - The banner description field is empty
     - :ref:`EvrV2CoreTriggers <entity-lcls-ii-evr-rtl-evrv2coretriggers-vhd>`
   * - header issues: ``LCLS-II/evr/rtl/EvrV2Module.vhd``
     - The banner description field is empty
     - :ref:`EvrV2Module <entity-lcls-ii-evr-rtl-evrv2module-vhd>`
   * - header issues: ``LCLS-II/evr/rtl/EvrV2Pkg.vhd``
     - The banner description field is empty
     - :ref:`EvrV2Pkg <package-evrv2pkg>`
   * - header issues: ``LCLS-II/evr/rtl/EvrV2TrigReg.vhd``
     - The banner description field is empty
     - :ref:`EvrV2TrigReg <entity-lcls-ii-evr-rtl-evrv2trigreg-vhd>`
   * - header issues: ``LCLS-II/evr/rtl/EvrV2Trigger.vhd``
     - The banner description contradicts what the file does
     - :ref:`EvrV2Trigger <entity-lcls-ii-evr-rtl-evrv2trigger-vhd>`
   * - header issues: ``LCLS-II/evr/tb/EvrV2_tb.vhd``
     - The banner description field is empty
     - :ref:`EvrV2_tb <entity-lcls-ii-evr-tb-evrv2-tb-vhd>`
   * - header issues: ``LCLS-II/gtp7/rtl/TimingGtCoreWrapper.vhd``
     - The banner description contradicts what the file does
     - :ref:`TimingGtCoreWrapper <entity-lcls-ii-gtp7-rtl-timinggtcorewrapper-vhd>`
