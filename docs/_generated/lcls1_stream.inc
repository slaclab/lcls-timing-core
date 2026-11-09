TimingStreamType: 704 bits, packed least significant bit first.

.. code-block:: text

   bits       width  field
   [31:0]     32     pulseId
   [287:32]   256    eventCodes
   [303:288]  16     dtype
   [319:304]  16     version
   [511:320]  192    dmod
   [575:512]  64     epicsTime
   [607:576]  32     edefAvgDn
   [639:608]  32     edefMinor
   [671:640]  32     edefMajor
   [703:672]  32     edefInit
   total: 704 bits
