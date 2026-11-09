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
   * - :ref:`BsaControl <entity-lcls-ii-core-rtl-bsacontrol-vhd>`
     - :repo:`LCLS-II/core/rtl/BsaControl.vhd`
     - not simulated: not loaded by any ruckus.tcl
     - issue pending
   * - :ref:`BsaControl <entity-lcls-ii-core-rtl-bsacontrolv2-vhd>`
     - :repo:`LCLS-II/core/rtl/BsaControlv2.vhd`
     - simulated
     - none
   * - :ref:`Divider <entity-lcls-ii-core-rtl-divider-vhd>`
     - :repo:`LCLS-II/core/rtl/Divider.vhd`
     - simulated
     - none
   * - :ref:`TPGMiniReg <entity-lcls-ii-core-rtl-tpgminireg-vhd>`
     - :repo:`LCLS-II/core/rtl/TPGMiniReg.vhd`
     - baseline-excluded
     - issue pending, issue pending

.. _entity-lcls-ii-core-rtl-bsacontrol-vhd:

BsaControl (LCLS-II/core/rtl/BsaControl.vhd)
--------------------------------------------

File: :repo:`LCLS-II/core/rtl/BsaControl.vhd`

Older definition of the entity BsaControl, the acquisition state of one BSA definition: it counts active cycles down from nToAvg and averages down from avgToWr, and treats an avgToWr of 0 as persist, as observed, intent unconfirmed. It has no tmo and tmocnt timeout inputs and no ruckus.tcl loads it, so the definition in use for this entity is BsaControlv2.vhd.

Status: not simulated: not loaded by any ruckus.tcl; declares entity BsaControl, which the loaded BsaControlv2.vhd also declares; TPGMini.vhd instantiates the loaded one

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
   * - ``ASYNC_REGCLK_G``
     - ``boolean``
     - ``false``

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``sysclk``
     - in
     - ``sl``
   * - ``sysrst``
     - in
     - ``sl``
   * - ``bsadef``
     - in
     - ``BsaDefType``
   * - ``nToAvgOut``
     - out
     - ``slv(15 downto 0)``
   * - ``avgToWrOut``
     - out
     - ``slv(15 downto 0)``
   * - ``txclk``
     - in
     - ``sl``
   * - ``txrst``
     - in
     - ``sl``
   * - ``enable``
     - in
     - ``sl``
   * - ``fixedRate``
     - in
     - ``slv(FIXEDRATEDEPTH - 1 downto 0)``
   * - ``acRate``
     - in
     - ``slv(ACRATEDEPTH - 1 downto 0)``
   * - ``acTS``
     - in
     - ``slv(2 downto 0)``
   * - ``beamSeq``
     - in
     - ``slv(31 downto 0)``
   * - ``expSeq``
     - in
     - ``Slv16Array(0 to 17)``
   * - ``bsaInit``
     - out
     - ``sl``
   * - ``bsaActive``
     - out
     - ``sl``
   * - ``bsaAvgDone``
     - out
     - ``sl``
   * - ``bsaDone``
     - out
     - ``sl``

Issues: issue pending

.. _entity-lcls-ii-core-rtl-bsacontrolv2-vhd:

BsaControl (LCLS-II/core/rtl/BsaControlv2.vhd)
----------------------------------------------

File: :repo:`LCLS-II/core/rtl/BsaControlv2.vhd`

Acquisition state of one BSA definition in the txclk domain: after the bsadef init input rises while enabled it pulses bsaInit, then drives bsaActive while the selected rate and destination match, bsaAvgDone at each average boundary set by nToAvg, and bsaDone after avgToWr averages, or never when avgToWr is 0xFFFF. The nToAvgOut and avgToWrOut status outputs count up, and the optional tmo and tmocnt inputs can assert bsaDone after an average. This is the definition of entity BsaControl that ruckus loads.

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
   * - ``ASYNC_REGCLK_G``
     - ``boolean``
     - ``false``

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``sysclk``
     - in
     - ``sl``
   * - ``sysrst``
     - in
     - ``sl``
   * - ``bsadef``
     - in
     - ``BsaDefType``
   * - ``tmo``
     - in
     - ``sl``
   * - ``tmocnt``
     - in
     - ``slv(3 downto 0)``
   * - ``nToAvgOut``
     - out
     - ``slv(15 downto 0)``
   * - ``avgToWrOut``
     - out
     - ``slv(15 downto 0)``
   * - ``txclk``
     - in
     - ``sl``
   * - ``txrst``
     - in
     - ``sl``
   * - ``enable``
     - in
     - ``sl``
   * - ``fixedRate``
     - in
     - ``slv(FIXEDRATEDEPTH - 1 downto 0)``
   * - ``acRate``
     - in
     - ``slv(ACRATEDEPTH - 1 downto 0)``
   * - ``acTS``
     - in
     - ``slv(2 downto 0)``
   * - ``beamSeq``
     - in
     - ``slv(31 downto 0)``
   * - ``expSeq``
     - in
     - ``Slv16Array(0 to 17)``
   * - ``bsaInit``
     - out
     - ``sl``
   * - ``bsaActive``
     - out
     - ``sl``
   * - ``bsaAvgDone``
     - out
     - ``sl``
   * - ``bsaDone``
     - out
     - ``sl``

Issues: none

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

.. _entity-lcls-ii-core-rtl-tpgminireg-vhd:

TPGMiniReg
----------

File: :repo:`LCLS-II/core/rtl/TPGMiniReg.vhd`

AXI-Lite register block of TPGMiniCore. It decodes the clock select, base divisor, fixed rate, pulse ID, timestamp, interval, and BSA definition registers into the TPGConfigType and TPGMiniEdefConfigType outputs, returns TPGStatusType counters on reads, and drives txReset, txLoopback, and txInhibit, while irqEnable and irqReq are tied low. GHDL cannot analyze this file, so its registers are checked through the PyRogue model and the register drift check.

Status: baseline-excluded; GHDL analysis reports "not locally static", which the regression records as a known failure

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
   * - ``NARRAYS_BSA``
     - ``integer``
     - ``1``
   * - ``USE_WSTRB_G``
     - ``boolean``
     - ``false``

.. rubric:: Ports

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Name
     - Direction
     - Type
   * - ``irqActive``
     - in
     - ``sl``
   * - ``irqEnable``
     - out
     - ``sl``
   * - ``irqReq``
     - out
     - ``sl``
   * - ``axiReadMaster``
     - in
     - ``AxiLiteReadMasterType``
   * - ``axiReadSlave``
     - out
     - ``AxiLiteReadSlaveType``
   * - ``axiWriteMaster``
     - in
     - ``AxiLiteWriteMasterType``
   * - ``axiWriteSlave``
     - out
     - ``AxiLiteWriteSlaveType``
   * - ``status``
     - in
     - ``TPGStatusType``
   * - ``config``
     - out
     - ``TPGConfigType``
   * - ``edefConfig``
     - out
     - ``TPGMiniEdefConfigType``
   * - ``txReset``
     - out
     - ``sl``
   * - ``txLoopback``
     - out
     - ``slv(2 downto 0)``
   * - ``txInhibit``
     - out
     - ``sl``
   * - ``axiClk``
     - in
     - ``sl``
   * - ``axiRst``
     - in
     - ``sl``

Issues: issue pending, issue pending
