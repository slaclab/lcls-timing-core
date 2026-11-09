PyRogue API
===========

``import LclsTimingCore`` makes every device class below available: the package ``__init__`` star imports each module, so ``LclsTimingCore.TPGControl`` and the other classes are one import away. Each page lists the constructor arguments with their defaults, the checks the constructor makes, the child devices, and the variables with offset, bits, mode, and description. The variables of a class that Rogue 6.16.0 builds come from the reviewed table checked against a built tree; the five classes Rogue rejects are read from the source. No page imports Rogue.

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Class
     - Builds under Rogue 6.16.0
     - Register page
   * - :ref:`EvrV2TriggerReg <api-evrv2triggerreg>`
     - yes
     - :ref:`EvrV2TriggerReg registers <register-map-evrv2triggerreg>`

.. toctree::
   :hidden:
   :maxdepth: 1

   EvrV2TriggerReg
