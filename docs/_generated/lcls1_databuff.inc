TimingDataBuffType: 416 bits, packed least significant bit first.

.. code-block:: text

   bits       width  field
   [15:0]     16     dtype
   [31:16]    16     version
   [223:32]   192    dmod
   [287:224]  64     epicsTime
   [319:288]  32     edefAvgDn
   [351:320]  32     edefMinor
   [383:352]  32     edefMajor
   [415:384]  32     edefInit
   total: 416 bits
