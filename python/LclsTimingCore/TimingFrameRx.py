#-----------------------------------------------------------------------------
# Title      : PyRogue Status of timing frame reception
#-----------------------------------------------------------------------------
# Description:
# PyRogue Status of timing frame reception
# Associated firmware: lcls-timing-core/LCLS-II/core/rtl/TimingRx.vhd
#-----------------------------------------------------------------------------
# This file is part of the 'LCLS Timing Core'. It is subject to
# the license terms in the LICENSE.txt file found in the top-level directory
# of this distribution and at:
#    https://confluence.slac.stanford.edu/display/ppareg/LICENSE.html.
# No part of the 'LCLS Timing Core', including this file, may be
# copied, modified, propagated, or distributed except according to the terms
# contained in the LICENSE.txt file.
#-----------------------------------------------------------------------------

import pyrogue as pr

class TimingFrameRx(pr.Device):
    def __init__(
            self,
            name        = "TimingFrameRx",
            description = "Status of timing frame reception",
            clkselMode  = 'SELECT',
            **kwargs):
        super().__init__(name=name, description=description, **kwargs)

        ##############################
        # Variables
        ##############################

        self.add(pr.RemoteVariable(
            name         = "sofCount",
            description  = "Start of frame count",
            offset       =  0x00,
            bitSize      =  32,
            bitOffset    =  0x00,
            mode         = "RO",
            pollInterval = 1,
        ))

        self.add(pr.RemoteVariable(
            name         = "eofCount",
            description  = "End of frame count",
            offset       =  0x04,
            bitSize      =  32,
            bitOffset    =  0x00,
            mode         = "RO",
            pollInterval = 1,
        ))

        self.add(pr.RemoteVariable(
            name         = "FidCount",
            description  = "Valid frame count",
            offset       =  0x08,
            bitSize      =  32,
            bitOffset    =  0x00,
            mode         = "RO",
            pollInterval = 1,
        ))

        self.add(pr.RemoteVariable(
            name         = "CrcErrCount",
            description  = "CRC error count",
            offset       =  0x0C,
            bitSize      =  32,
            bitOffset    =  0x00,
            mode         = "RO",
            pollInterval = 1,
        ))

        self.add(pr.RemoteVariable(
            name         = "RxClkCount",
            description  = "Recovered clock count div 16",
            offset       =  0x10,
            bitSize      =  32,
            bitOffset    =  0x00,
            mode         = "RO",
            pollInterval = 1,
        ))

        self.add(pr.RemoteVariable(
            name         = "RxRstCount",
            description  = "Receive link reset count",
            offset       =  0x14,
            bitSize      =  32,
            bitOffset    =  0x00,
            mode         = "RO",
            pollInterval = 1,
        ))

        self.add(pr.RemoteVariable(
            name         = "RxDecErrCount",
            description  = "Receive 8b/10b decode error count",
            offset       =  0x18,
            bitSize      =  32,
            bitOffset    =  0x00,
            mode         = "RO",
            pollInterval = 1,
        ))

        self.add(pr.RemoteVariable(
            name         = "RxDspErrCount",
            description  = "Receive disparity error count",
            offset       =  0x1C,
            bitSize      =  32,
            bitOffset    =  0x00,
            mode         = "RO",
            pollInterval = 1,
        ))

        self.add(pr.RemoteCommand(
            name         = "ClearRxCounters",
            description  = "Reset receive counters",
            offset       =  0x20,
            bitSize      =  1,
            bitOffset    =  0x00,
            function     = pr.RemoteCommand.toggle
        ))

        self.add(pr.RemoteVariable(
            name         = "RxLinkUp",
            description  = "Receive link status",
            offset       =  0x20,
            bitSize      =  1,
            bitOffset    =  0x01,
            mode         = "RO",
            pollInterval = 1,
        ))

        self.add(pr.RemoteVariable(
            name         = "RxPolarity",
            description  = "Invert receive link polarity",
            offset       =  0x20,
            bitSize      =  1,
            bitOffset    =  0x02,
            mode         = "RW",
        ))

        self.add(pr.RemoteCommand(
            name         = "C_RxReset",
            description  = "Reset receive link",
            offset       =  0x20,
            bitSize      =  1,
            bitOffset    =  0x03,
            function     = pr.RemoteCommand.toggle
        ))

        self.add(pr.RemoteVariable(
            name         = "ClkSel",
            description  = "Select LCLS-I/LCLS-II Timing",
            offset       =  0x20,
            bitSize      =  1,
            bitOffset    =  0x04,
            mode         = "RW" if clkselMode == 'SELECT' else 'RO',
            enum         = {
                0: 'LCLS-I Clock',
                1: 'LCLS-II Clock'}
        ))

        self.add(pr.RemoteVariable(
            name         = "RxDown",
            description  = "Rx down latch status",
            offset       =  0x20,
            bitSize      =  1,
            bitOffset    =  0x05,
            mode         = "RW",
            verify       = False,
        ))

        self.add(pr.RemoteVariable(
            name         = "BypassRst",
            description  = "Buffer bypass reset status",
            offset       =  0x20,
            bitSize      =  1,
            bitOffset    =  0x06,
            mode         = "RW",
        ))

        self.add(pr.RemoteVariable(
            name         = "RxPllReset",
            description  = "Reset RX PLL",
            offset       = 0x20,
            bitSize      = 1,
            bitOffset    = 0x07,
            mode         = "WO",
        ))

        self.add(pr.RemoteVariable(
            name         = "ModeSel",
            description  = "Select timing mode",
            offset       = 0x20,
            bitSize      = 1,
            bitOffset    = 0x09,
            mode         = "RW" if clkselMode == 'SELECT' else 'RO',
            verify       = False, # No verification because axilR.modeSelEn=0x0 can overwrite ModeSel with ClkSel
            enum         = {
                0x0: 'Lcls1Protocol',
                0x1: 'Lcls2Protocol',
            },
        ))

        self.add(pr.RemoteVariable(
            name         = "ModeSelEn",
            description  = "Enable ModeSel register",
            offset       = 0x20,
            bitSize      = 1,
            bitOffset    = 0x0A,
            mode         = "RW" if clkselMode == 'SELECT' else 'RO',
            enum         = {
                0x0: 'UseClkSel',
                0x1: 'UseModeSel',
            },
        ))

        self.add(pr.RemoteVariable(
            name         = "MsgDelay",
            description  = "LCLS-II timing frame pipeline delay (186MHz clks)",
            offset       =  0x24,
            bitSize      =  20,
            bitOffset    =  0x00,
            mode         = "RW",
        ))

        self.add(pr.RemoteVariable(
            name         = "TxClkCount",
            description  = "Transmit clock counter div 16",
            offset       =  0x28,
            bitSize      =  32,
            bitOffset    =  0x00,
            mode         = "RO",
            pollInterval = 1,
        ))

        self.add(pr.RemoteVariable(
            name         = "BypassDoneCount",
            description  = "Buffer bypass done count",
            offset       =  0x2C,
            bitSize      =  16,
            bitOffset    =  0x00,
            mode         = "RO",
            pollInterval = 1,
        ))

        self.add(pr.RemoteVariable(
            name         = "BypassResetCount",
            description  = "Buffer bypass reset count",
            offset       =  0x2C,
            bitSize      =  16,
            bitOffset    =  16,
            mode         = "RO",
            pollInterval = 1,
        ))

    def hardReset(self):
        self.ClearRxCounters()
        self.RxDown.set(0)

    def softReset(self):
        self.ClearRxCounters()
        self.RxDown.set(0)

    def countReset(self):
        self.ClearRxCounters()
        self.RxDown.set(0)
