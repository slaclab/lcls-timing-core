.. _api-evrv1isr:

EvrV1Isr
========

Source: :repo:`python/LclsTimingCore/EvrV1Isr.py`. Register table: :ref:`EvrV1Isr registers <register-map-evrv1isr>`.

Constructor
-----------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Argument
     - Default
   * - ``name``
     - ``'EvrV1Isr'``
   * - ``description``
     - ``'LCLS-I EVR ISR Controller'``
   * - ``**kwargs``
     - none

Arguments beyond the ``pr.Device`` defaults: none.

Constructor checks
------------------

none

Sub-devices
-----------

none

Variables
---------

Arguments default
~~~~~~~~~~~~~~~~~

Constructor arguments: none.

.. list-table::
   :header-rows: 1
   :widths: 17 11 12 7 6 14 10 23

   * - Name
     - Kind
     - Offset
     - Bits
     - Mode
     - Base or enum
     - Condition
     - Description
   * - ``IsrSelect``
     - RemoteVariable
     - ``0x000``
     - [0]
     - RW
     - UInt
     - none
     - 0x1 = Software ISR, 0x0 = Firmware ISR

Known issues
------------

none
