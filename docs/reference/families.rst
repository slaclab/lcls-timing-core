FPGA families, Vivado, and coregen
==================================

:repo:`LCLS-II/ruckus.tcl` asks ruckus for the FPGA family of the build and loads the transceiver wrapper directories listed here. The table has one row for each family and directory, so a family that loads two directories has two rows.

.. list-table::
   :header-rows: 1
   :widths: 11 17 14 11 30 17

   * - Family
     - Directory
     - Wrapper entity
     - Vivado gate on the RTL
     - Coregen IP loaded
     - Selected by
   * - artix7
     - :repo:`LCLS-II/gtp7/ruckus.tcl`
     - TimingGtCoreWrapper
     - none
     - none
     - none
   * - kintex7
     - :repo:`LCLS-II/gtx7/ruckus.tcl`
     - TimingGtCoreWrapper
     - none
     - none
     - none
   * - kintexu
     - :repo:`LCLS-II/gthUltraScale/ruckus.tcl`
     - TimingGtCoreWrapper
     - Vivado >= 2016.4
     - - coregen/2025.1 (xci): TimingGth_extref, TimingGth_fixedlat; Vivado >= 2025.1, LCLS_TIMING_GTH_XCI = 1
       - coregen/2025.1 (dcp): TimingGth_extref, TimingGth_fixedlat; Vivado >= 2025.1, LCLS_TIMING_GTH_XCI not 1
       - coregen/2025.1 (xdc): TimingGth_fixedlat; Vivado >= 2025.1, LCLS_TIMING_GTH_XCI not 1
       - coregen/2016.4 (xci): TimingGth_extref, TimingGth_fixedlat; Vivado >= 2016.4 and < 2025.1, LCLS_TIMING_GTH_XCI = 1
       - coregen/2016.4 (dcp): TimingGth_extref, TimingGth_fixedlat; Vivado >= 2016.4 and < 2025.1, LCLS_TIMING_GTH_XCI not 1
     - - LCLS_TIMING_GTH_XCI = 1: file type xci
       - LCLS_TIMING_GTH_XCI not 1: file type dcp, xdc
   * - kintexuplus
     - :repo:`LCLS-II/gtyUltraScale+/ruckus.tcl`
     - TimingGtCoreWrapper
     - none
     - - coregen (xci): TimingGty_extref, TimingGty_fixedlat, TimingGty_fixedlat_Lcls1Only; Vivado >= 2021.1, TIMING_246MHz unset or 0, LCLS_TIMING_GTY_XCI = 1
       - coregen (dcp): TimingGty_extref, TimingGty_fixedlat, TimingGty_fixedlat_Lcls1Only; Vivado >= 2021.1, TIMING_246MHz unset or 0, LCLS_TIMING_GTY_XCI not 1
       - coregen/smurf (xci): TimingGty_extref, TimingGty_fixedlat; Vivado >= 2018.2, TIMING_246MHz set and not 0, LCLS_TIMING_GTY_XCI = 1
       - coregen/smurf (dcp): TimingGty_extref, TimingGty_fixedlat; Vivado >= 2018.2, TIMING_246MHz set and not 0, LCLS_TIMING_GTY_XCI not 1
     - - TIMING_246MHz unset or 0: directory coregen
       - TIMING_246MHz set and not 0: directory coregen/smurf
       - LCLS_TIMING_GTY_XCI = 1: file type xci
       - LCLS_TIMING_GTY_XCI not 1: file type dcp
   * - virtexuplus
     - :repo:`LCLS-II/gtyUltraScale+/ruckus.tcl`
     - TimingGtCoreWrapper
     - none
     - - coregen (xci): TimingGty_extref, TimingGty_fixedlat, TimingGty_fixedlat_Lcls1Only; Vivado >= 2021.1, TIMING_246MHz unset or 0, LCLS_TIMING_GTY_XCI = 1
       - coregen (dcp): TimingGty_extref, TimingGty_fixedlat, TimingGty_fixedlat_Lcls1Only; Vivado >= 2021.1, TIMING_246MHz unset or 0, LCLS_TIMING_GTY_XCI not 1
       - coregen/smurf (xci): TimingGty_extref, TimingGty_fixedlat; Vivado >= 2018.2, TIMING_246MHz set and not 0, LCLS_TIMING_GTY_XCI = 1
       - coregen/smurf (dcp): TimingGty_extref, TimingGty_fixedlat; Vivado >= 2018.2, TIMING_246MHz set and not 0, LCLS_TIMING_GTY_XCI not 1
     - - TIMING_246MHz unset or 0: directory coregen
       - TIMING_246MHz set and not 0: directory coregen/smurf
       - LCLS_TIMING_GTY_XCI = 1: file type xci
       - LCLS_TIMING_GTY_XCI not 1: file type dcp
   * - virtexuplusHBM
     - :repo:`LCLS-II/gtyUltraScale+/ruckus.tcl`
     - TimingGtCoreWrapper
     - none
     - - coregen (xci): TimingGty_extref, TimingGty_fixedlat, TimingGty_fixedlat_Lcls1Only; Vivado >= 2021.1, TIMING_246MHz unset or 0, LCLS_TIMING_GTY_XCI = 1
       - coregen (dcp): TimingGty_extref, TimingGty_fixedlat, TimingGty_fixedlat_Lcls1Only; Vivado >= 2021.1, TIMING_246MHz unset or 0, LCLS_TIMING_GTY_XCI not 1
       - coregen/smurf (xci): TimingGty_extref, TimingGty_fixedlat; Vivado >= 2018.2, TIMING_246MHz set and not 0, LCLS_TIMING_GTY_XCI = 1
       - coregen/smurf (dcp): TimingGty_extref, TimingGty_fixedlat; Vivado >= 2018.2, TIMING_246MHz set and not 0, LCLS_TIMING_GTY_XCI not 1
     - - TIMING_246MHz unset or 0: directory coregen
       - TIMING_246MHz set and not 0: directory coregen/smurf
       - LCLS_TIMING_GTY_XCI = 1: file type xci
       - LCLS_TIMING_GTY_XCI not 1: file type dcp
   * - zynquplus
     - :repo:`LCLS-II/gtyUltraScale+/ruckus.tcl`
     - TimingGtCoreWrapper
     - none
     - - coregen (xci): TimingGty_extref, TimingGty_fixedlat, TimingGty_fixedlat_Lcls1Only; Vivado >= 2021.1, TIMING_246MHz unset or 0, LCLS_TIMING_GTY_XCI = 1
       - coregen (dcp): TimingGty_extref, TimingGty_fixedlat, TimingGty_fixedlat_Lcls1Only; Vivado >= 2021.1, TIMING_246MHz unset or 0, LCLS_TIMING_GTY_XCI not 1
       - coregen/smurf (xci): TimingGty_extref, TimingGty_fixedlat; Vivado >= 2018.2, TIMING_246MHz set and not 0, LCLS_TIMING_GTY_XCI = 1
       - coregen/smurf (dcp): TimingGty_extref, TimingGty_fixedlat; Vivado >= 2018.2, TIMING_246MHz set and not 0, LCLS_TIMING_GTY_XCI not 1
     - - TIMING_246MHz unset or 0: directory coregen
       - TIMING_246MHz set and not 0: directory coregen/smurf
       - LCLS_TIMING_GTY_XCI = 1: file type xci
       - LCLS_TIMING_GTY_XCI not 1: file type dcp
   * - zynquplusRFSOC
     - :repo:`LCLS-II/gtyUltraScale+/ruckus.tcl`
     - TimingGtCoreWrapper
     - none
     - - coregen (xci): TimingGty_extref, TimingGty_fixedlat, TimingGty_fixedlat_Lcls1Only; Vivado >= 2021.1, TIMING_246MHz unset or 0, LCLS_TIMING_GTY_XCI = 1
       - coregen (dcp): TimingGty_extref, TimingGty_fixedlat, TimingGty_fixedlat_Lcls1Only; Vivado >= 2021.1, TIMING_246MHz unset or 0, LCLS_TIMING_GTY_XCI not 1
       - coregen/smurf (xci): TimingGty_extref, TimingGty_fixedlat; Vivado >= 2018.2, TIMING_246MHz set and not 0, LCLS_TIMING_GTY_XCI = 1
       - coregen/smurf (dcp): TimingGty_extref, TimingGty_fixedlat; Vivado >= 2018.2, TIMING_246MHz set and not 0, LCLS_TIMING_GTY_XCI not 1
     - - TIMING_246MHz unset or 0: directory coregen
       - TIMING_246MHz set and not 0: directory coregen/smurf
       - LCLS_TIMING_GTY_XCI = 1: file type xci
       - LCLS_TIMING_GTY_XCI not 1: file type dcp
   * - qzynquplusRFSOC
     - :repo:`LCLS-II/gtyUltraScale+/ruckus.tcl`
     - TimingGtCoreWrapper
     - none
     - - coregen (xci): TimingGty_extref, TimingGty_fixedlat, TimingGty_fixedlat_Lcls1Only; Vivado >= 2021.1, TIMING_246MHz unset or 0, LCLS_TIMING_GTY_XCI = 1
       - coregen (dcp): TimingGty_extref, TimingGty_fixedlat, TimingGty_fixedlat_Lcls1Only; Vivado >= 2021.1, TIMING_246MHz unset or 0, LCLS_TIMING_GTY_XCI not 1
       - coregen/smurf (xci): TimingGty_extref, TimingGty_fixedlat; Vivado >= 2018.2, TIMING_246MHz set and not 0, LCLS_TIMING_GTY_XCI = 1
       - coregen/smurf (dcp): TimingGty_extref, TimingGty_fixedlat; Vivado >= 2018.2, TIMING_246MHz set and not 0, LCLS_TIMING_GTY_XCI not 1
     - - TIMING_246MHz unset or 0: directory coregen
       - TIMING_246MHz set and not 0: directory coregen/smurf
       - LCLS_TIMING_GTY_XCI = 1: file type xci
       - LCLS_TIMING_GTY_XCI not 1: file type dcp
   * - kintexuplus
     - :repo:`LCLS-II/gthUltraScale+/ruckus.tcl`
     - TimingGthCoreWrapper
     - Vivado >= 2022.2
     - - coregen (xci): TimingGth_extref, TimingGth_fixedlat; Vivado >= 2022.2, LCLS_TIMING_GTH_XCI = 1
       - coregen (dcp): TimingGth_extref, TimingGth_fixedlat; Vivado >= 2022.2, LCLS_TIMING_GTH_XCI not 1
     - - LCLS_TIMING_GTH_XCI = 1: file type xci
       - LCLS_TIMING_GTH_XCI not 1: file type dcp
   * - virtexuplus
     - :repo:`LCLS-II/gthUltraScale+/ruckus.tcl`
     - TimingGthCoreWrapper
     - Vivado >= 2022.2
     - - coregen (xci): TimingGth_extref, TimingGth_fixedlat; Vivado >= 2022.2, LCLS_TIMING_GTH_XCI = 1
       - coregen (dcp): TimingGth_extref, TimingGth_fixedlat; Vivado >= 2022.2, LCLS_TIMING_GTH_XCI not 1
     - - LCLS_TIMING_GTH_XCI = 1: file type xci
       - LCLS_TIMING_GTH_XCI not 1: file type dcp
   * - virtexuplusHBM
     - :repo:`LCLS-II/gthUltraScale+/ruckus.tcl`
     - TimingGthCoreWrapper
     - Vivado >= 2022.2
     - - coregen (xci): TimingGth_extref, TimingGth_fixedlat; Vivado >= 2022.2, LCLS_TIMING_GTH_XCI = 1
       - coregen (dcp): TimingGth_extref, TimingGth_fixedlat; Vivado >= 2022.2, LCLS_TIMING_GTH_XCI not 1
     - - LCLS_TIMING_GTH_XCI = 1: file type xci
       - LCLS_TIMING_GTH_XCI not 1: file type dcp
   * - zynquplus
     - :repo:`LCLS-II/gthUltraScale+/ruckus.tcl`
     - TimingGthCoreWrapper
     - Vivado >= 2022.2
     - - coregen (xci): TimingGth_extref, TimingGth_fixedlat; Vivado >= 2022.2, LCLS_TIMING_GTH_XCI = 1
       - coregen (dcp): TimingGth_extref, TimingGth_fixedlat; Vivado >= 2022.2, LCLS_TIMING_GTH_XCI not 1
     - - LCLS_TIMING_GTH_XCI = 1: file type xci
       - LCLS_TIMING_GTH_XCI not 1: file type dcp
   * - zynquplusRFSOC
     - :repo:`LCLS-II/gthUltraScale+/ruckus.tcl`
     - TimingGthCoreWrapper
     - Vivado >= 2022.2
     - - coregen (xci): TimingGth_extref, TimingGth_fixedlat; Vivado >= 2022.2, LCLS_TIMING_GTH_XCI = 1
       - coregen (dcp): TimingGth_extref, TimingGth_fixedlat; Vivado >= 2022.2, LCLS_TIMING_GTH_XCI not 1
     - - LCLS_TIMING_GTH_XCI = 1: file type xci
       - LCLS_TIMING_GTH_XCI not 1: file type dcp
   * - qzynquplusRFSOC
     - :repo:`LCLS-II/gthUltraScale+/ruckus.tcl`
     - TimingGthCoreWrapper
     - Vivado >= 2022.2
     - - coregen (xci): TimingGth_extref, TimingGth_fixedlat; Vivado >= 2022.2, LCLS_TIMING_GTH_XCI = 1
       - coregen (dcp): TimingGth_extref, TimingGth_fixedlat; Vivado >= 2022.2, LCLS_TIMING_GTH_XCI not 1
     - - LCLS_TIMING_GTH_XCI = 1: file type xci
       - LCLS_TIMING_GTH_XCI not 1: file type dcp

The coregen column lists, for each Vivado version range and environment variable setting, the directory, the file type, and the IP cores that the directory's ``ruckus.tcl`` loads. Outside the listed ranges the directory loads no IP and its ``ruckus.tcl`` prints a warning.

The transceiver wrappers are not simulated in CI, see :doc:`entities/gt`.

Version checks and locks
------------------------

Every ``VersionCheck`` and ``SubmoduleCheck`` in the repository's ``ruckus.tcl`` files, as found.

.. list-table::
   :header-rows: 1
   :widths: 35 20 15 15 15

   * - File
     - Check
     - Name
     - Version
     - Issues
   * - :repo:`ruckus.tcl`
     - VersionCheck
     - Vivado
     - 2019.1
     - none
   * - :repo:`ruckus.tcl`
     - SubmoduleCheck
     - ruckus
     - 2.1.2
     - none
   * - :repo:`ruckus.tcl`
     - SubmoduleCheck
     - surf
     - 2.53.0
     - :issue:`229`
   * - :repo:`LCLS-II/gtx7/ruckus.tcl`
     - SubmoduleCheck
     - surf
     - 2.74.0
     - :issue:`229`
