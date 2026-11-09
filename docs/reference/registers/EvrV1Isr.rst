EvrV1Isr registers
==================

Decode file: :repo:`LCLS-I/evr/EvrV1CoreIsrCtrl.vhd`. Python class: :repo:`python/LclsTimingCore/EvrV1Isr.py`. YAML map: :repo:`yaml/EvrV1Isr.yaml`.

Variant default
---------------

RTL generics: none. Python arguments: none.

.. list-table::
   :header-rows: 1
   :widths: 9 17 7 6 12 15 15 19

   * - Offset
     - Field
     - Bits
     - Mode
     - Reset
     - Python
     - YAML
     - Description
   * - ``0x000``
     - ``IsrSelect``
       RTL: ``isrSelect``
     - [0]
     - RW
     - not asserted
     - agrees
     - agrees
     - 0x1 = Software ISR, 0x0 = Firmware ISR

