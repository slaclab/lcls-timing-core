LCLS-I frame for pulse id 0, no event code set, and an all-zero data buffer, without the idle fill: 684 symbols, one per clock.

.. code-block:: text

   symbols  sequence                        data16                    K flags
   1        start                           0x1C00                    10
   104      52 x (comma, data buffer byte)  0x00BC, data              01, 00
   1        end                             0x3CBC                    11
   64       32 x (pulse id bit, comma)      0x0070 or 0x0071, 0x00BC  00, 01
   1        event-code marker               0x007D                    00
   512      256 x (comma, unset code slot)  0x00BC, 0x0000            01, 00
   1        comma                           0x00BC                    01
   total: 684 symbols
