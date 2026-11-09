.. _api-evrv2corechannels:

EvrV2CoreChannels
=================

Source: :repo:`python/LclsTimingCore/EvrV2CoreChannels.py`. Register table: :ref:`EvrV2ChannelReg registers <register-map-evrv2channelreg>`.

Constructor
-----------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Argument
     - Default
   * - ``name``
     - ``'EvrV2CoreChannels'``
   * - ``description``
     - ``'https://confluence.slac.stanford.edu/download/attachments/216713616/ConfigEvrV2CoreTriggersYaml.pdf'``
   * - ``numTrig``
     - ``1``
   * - ``dmaEnable``
     - ``False``
   * - ``useTap``
     - ``False``
   * - ``tickUnit``
     - ``'TBD'``
   * - ``**kwargs``
     - none

Constructor checks
------------------

The constructor raises ``ValueError`` when:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Condition
     - Message
   * - ``numTrig < 1 or numTrig > 16``
     - ``'numTrig must be between 1 to 16: (%i) is out of range' % numTrig``

Sub-devices
-----------

.. list-table::
   :header-rows: 1
   :widths: 25 30 15 15 15

   * - Name
     - Class
     - Offset
     - Count
     - Stride
   * - ``EvrV2ChannelReg``
     - :ref:`EvrV2ChannelReg <api-evrv2channelreg>`
     - ``0x0``
     - numTrig
     - ``0x100``

Variables
---------

none

Known issues
------------

none
