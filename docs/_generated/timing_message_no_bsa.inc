TimingMessageType without BSA (toSlvNoBsa): 672 bits, packed least significant bit first.

.. code-block:: text

   bits       width    field
   [63:0]     64       pulseId
   [127:64]   64       timeStamp
   [137:128]  10       fixedRates
   [143:138]  6        acRates
   [146:144]  3        acTimeSlot
   [158:147]  12       acTimeSlotPhase
   [159:159]  1        resync
   [191:160]  32       beamRequest
   [255:192]  4 x 16   beamEnergy[0..3]
   [287:256]  2 x 16   photonWavelen[0..1]
   [303:288]  16       modifier
   [319:304]  16       mpsLimit
   [383:320]  16 x 4   mpsClass[0..15]
   [671:384]  18 x 16  control[0..17]
   total: 672 bits
