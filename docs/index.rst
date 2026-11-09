lcls-timing-core
================

lcls-timing-core is the SLAC LCLS-I and LCLS-II timing firmware library. It
holds the family-agnostic timing receiver core, the LCLS-II event receiver
(EVR), the legacy LCLS-I EVR, the per-family transceiver (GT) wrappers, the
``LclsTimingCore`` PyRogue drivers, and the YAML register maps that describe
the same registers.

The how-to guides give short recipes for common tasks. The reference lists
the entities, registers, PyRogue classes, and known issues. The explanation
pages describe how the blocks fit together and why.

.. toctree::
   :maxdepth: 2

   how-to/index
   reference/index
   explanation/index
