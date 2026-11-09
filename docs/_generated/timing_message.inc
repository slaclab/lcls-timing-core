TimingMessageType: 944 bits, packed least significant bit first.

.. code-block:: text

   bits       width    field
   [15:0]     16       version
   [79:16]    64       pulseId
   [143:80]   64       timeStamp
   [153:144]  10       fixedRates
   [159:154]  6        acRates
   [162:160]  3        acTimeSlot
   [174:163]  12       acTimeSlotPhase
   [175:175]  1        resync
   [207:176]  32       beamRequest
   [271:208]  4 x 16   beamEnergy[0..3]
   [303:272]  2 x 16   photonWavelen[0..1]
   [316:304]  13       unused
   [317:317]  1        syncStatus
   [318:318]  1        mpsValid
   [319:319]  1        bcsFault
   [335:320]  16       mpsLimit
   [399:336]  16 x 4   mpsClass[0..15]
   [463:400]  64       bsaInit
   [527:464]  64       bsaActive
   [591:528]  64       bsaAvgDone
   [655:592]  64       bsaDone
   [943:656]  18 x 16  control[0..17]
   total: 944 bits
