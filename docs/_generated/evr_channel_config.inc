EvrV2ChannelConfig: 81 bits, packed least significant bit first.

.. code-block:: text

   bits     width  field
   [0:0]    1      enabled
   [13:1]   13     rateSel
   [32:14]  19     destSel
   [33:33]  1      bsaEnabled
   [39:34]  6      bsaActiveSetup
   [59:40]  20     bsaActiveDelay
   [79:60]  20     bsaActiveWidth
   [80:80]  1      dmaEnabled
   total: 81 bits
