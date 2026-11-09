EvrV2TriggerConfigType: 87 bits, packed least significant bit first.

.. code-block:: text

   bits     width  field
   [0:0]    1      enabled
   [1:1]    1      polarity
   [2:2]    1      complEn
   [3:3]    1      complAnd
   [31:4]   28     delay
   [59:32]  28     width
   [63:60]  4      channel
   [79:64]  16     channels
   [85:80]  6      delayTap
   [86:86]  1      loadTap
   total: 87 bits
