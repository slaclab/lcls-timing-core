LCLS-II frame of the default message on stream 0 (every field at its reset value): 66 symbols, one per clock.

.. code-block:: text

   symbols  sequence         data16  K flags
   1        alignment comma  0xB53C  01
   1        SOF              0xB5F7  01
   1        SOS              0x0080  00
   59       data words       data    00
   1        EOS              0xB51C  01
   1        EOF              0xB5FD  01
   1        CRC low word     0xB9B8  00
   1        CRC high word    0x64A7  00
   total: 66 symbols
