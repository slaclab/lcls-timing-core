LCLS-II core
============

:repo:`LCLS-II/core/ruckus.tcl` loads these sources into the ``lcls_timing_core`` library; a file it does not load says so in the Status column.

.. list-table::
   :header-rows: 1
   :widths: 20 40 25 15

   * - Entity
     - File
     - Status
     - Issues
   * - :ref:`Divider <entity-lcls-ii-core-rtl-divider-vhd>`
     - :repo:`LCLS-II/core/rtl/Divider.vhd`
     - simulated
     - none

.. _entity-lcls-ii-core-rtl-divider-vhd:

Divider
-------

File: :repo:`LCLS-II/core/rtl/Divider.vhd`

Prescaler that raises trigO for one sysClk cycle every divisor cycles while enable is high, counting from 1 up to divisor and restarting at 1. Holding enable low freezes the count and the trigO level, clear with enable low forces trigO low, and sysReset restarts the count at 1 and drops trigO. A divisor of 0 never matches until the Width-bit counter wraps, so at the default Width of 4 the period is 16 cycles.

Status: simulated

.. rubric:: Generics

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Name
     - Type
     - Default
   * - ``TPD_G``
     - ``time``
     - ``1 ns``
   * - ``Width``
     - ``integer``
     - ``4``

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``sysClk``
     - in
     - ``std_logic``
   * - ``sysReset``
     - in
     - ``std_logic``
   * - ``enable``
     - in
     - ``std_logic``
   * - ``clear``
     - in
     - ``std_logic``
   * - ``divisor``
     - in
     - ``std_logic_vector(Width - 1 downto 0)``
   * - ``trigO``
     - out
     - ``std_logic``

Issues: none
