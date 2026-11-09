PyRogue API
===========

``import LclsTimingCore`` makes every device class below available: the package ``__init__`` star imports each module, so ``LclsTimingCore.TPGControl`` and the other classes are one import away. Each page lists the constructor arguments with their defaults, the checks the constructor makes, the child devices, and the variables with offset, bits, mode, and description. The variables of a class that Rogue 6.16.0 builds come from the reviewed table checked against a built tree; the 5 classes Rogue rejects are read from the source. No page imports Rogue.

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Class
     - Builds under Rogue 6.16.0
     - Register page
   * - :ref:`EvrV1Isr <api-evrv1isr>`
     - yes
     - :ref:`EvrV1Isr registers <register-map-evrv1isr>`
   * - :ref:`EvrV1Reg <api-evrv1reg>`
     - no: rejected at ``root.start()``
     - :ref:`EvrV1Reg registers <register-map-evrv1reg>`
   * - :ref:`EvrV2ChannelReg <api-evrv2channelreg>`
     - yes
     - :ref:`EvrV2ChannelReg registers <register-map-evrv2channelreg>`
   * - :ref:`EvrV2Core <api-evrv2core>`
     - yes
     - :ref:`EvrV2Core registers <register-map-evrv2core>`
   * - :ref:`EvrV2CoreChannels <api-evrv2corechannels>`
     - yes
     - :ref:`EvrV2ChannelReg registers <register-map-evrv2channelreg>`
   * - :ref:`EvrV2CoreTriggers <api-evrv2coretriggers>`
     - yes
     - :ref:`EvrV2CoreTriggers registers <register-map-evrv2coretriggers>`
   * - :ref:`EvrV2TriggerReg <api-evrv2triggerreg>`
     - yes
     - :ref:`EvrV2TriggerReg registers <register-map-evrv2triggerreg>`
   * - :ref:`GthRxAlignCheck <api-gthrxaligncheck>`
     - yes
     - :ref:`GthRxAlignCheck registers <register-map-gthrxaligncheck>`
   * - :ref:`LclsTriggerPulse <api-lclstriggerpulse>`
     - yes
     - :ref:`LclsTriggerPulse registers <register-map-lclstriggerpulse>`
   * - :ref:`TPG <api-tpg>`
     - no: rejected at ``root.start()``
     - :ref:`TPG registers <register-map-tpg>`
   * - :ref:`TPGControl <api-tpgcontrol>`
     - yes
     - :ref:`TPGControl registers <register-map-tpgcontrol>`
   * - :ref:`TPGMiniCore <api-tpgminicore>`
     - yes
     - :ref:`TPGMiniCore registers <register-map-tpgminicore>`
   * - :ref:`TPGSeqJump <api-tpgseqjump>`
     - no: rejected at ``root.start()``
     - :ref:`TPGSeqJump registers <register-map-tpgseqjump>`
   * - :ref:`TPGSeqState <api-tpgseqstate>`
     - no: rejected at ``root.start()``
     - :ref:`TPGSeqState registers <register-map-tpgseqstate>`
   * - :ref:`TPGStatus <api-tpgstatus>`
     - no: rejected at ``root.start()``
     - :ref:`TPGStatus registers <register-map-tpgstatus>`
   * - :ref:`TimingFrameRx <api-timingframerx>`
     - yes
     - :ref:`TimingFrameRx registers <register-map-timingframerx>`

.. toctree::
   :hidden:
   :maxdepth: 1

   EvrV1Isr
   EvrV1Reg
   EvrV2ChannelReg
   EvrV2Core
   EvrV2CoreChannels
   EvrV2CoreTriggers
   EvrV2TriggerReg
   GthRxAlignCheck
   LclsTriggerPulse
   TPG
   TPGControl
   TPGMiniCore
   TPGSeqJump
   TPGSeqState
   TPGStatus
   TimingFrameRx
