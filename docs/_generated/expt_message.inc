ExptMessageType: 320 bits, packed least significant bit first.

.. code-block:: text

   bits      width  field
   [31:0]    32     baseRateSince1Hz
   [63:32]   32     baseRateSinceTM
   [319:64]  256    irigTimeCode
   total: 320 bits
