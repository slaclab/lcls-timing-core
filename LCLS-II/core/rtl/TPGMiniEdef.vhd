library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.StdRtlPkg.all;
use work.TPGMiniEdefPkg.all;
use work.TextUtilPkg.all;

entity TPGMiniEdef is
   generic (
      TPD_G  : time     := 1 ns;
      EDEF_G : EdefType := (others => '0')
   );
   port (
      clk   : in  sl;
      rst   : in  sl;
      cen   : in  sl;

      strb  : in  sl;

      cnfg  : in TPGMiniEdefConfigType;

      actv  : out sl;
      avgD  : out sl;
      allD  : out sl;
      init  : out sl;
      smin  : out sl;
      smaj  : out sl;
      rate  : out EdefRateType;
      slot  : out EdefTSType
   );
end entity TPGMiniEdef;

architecture TPGMiniEdefImpl of TPGMiniEdef is

   subtype NsmpType is natural range 0 to 2800;

   type RegType is record
      cnfg : TPGMiniEdefConfigType;
      avgc : EdefNavgType;
      actv : sl;
      init : sl;
   end record RegType;

   constant REG_INIT_C : RegType := (
      cnfg => TPG_MINI_EDEF_CONFIG_INIT_C,
      avgc => (others => '0'),
      actv => '0',
      init => '0'
   );

   signal r   : RegType := REG_INIT_C;
   signal rin : RegType;

   signal avgDon : sl;
   signal allDon : sl;

begin

   avgDon <= r.actv and ite( unsigned(r.avgc) = 0 , '1', '0' );
   allDon <= avgDon and ite( unsigned(r.cnfg.nsmp) = 0 , '1', '0' );

   P_COMB : process(r, strb, cnfg, avgDon, allDon) is
      variable v : RegType;
   begin
      v := r;

      v.init := '0';

      if ( r.actv = '1' ) then
         if ( strb = '1' ) then
            if ( avgDon = '1' ) then
               if ( allDon = '1' ) then
                  v.actv := '0';
               else
                  v.cnfg.nsmp := slv(unsigned(r.cnfg.nsmp) - 1);
                  v.avgc := r.cnfg.navg;
               end if;
            else
               v.avgc := slv(unsigned(r.avgc) - 1);
            end if;
         end if;
      elsif ( r.init = '1' ) then
         -- AFAIK, traditionally edefInit precedes the earliest 'active'...
         v.actv := '1';
      elsif ( cnfg.wrEn = '1' and cnfg.edef = EDEF_G ) then
         v.cnfg := cnfg;
         v.avgc := cnfg.navg;
         v.init := '1';
      end if;
   
      rin <= v;
   end process P_COMB;

   P_SEQ : process(clk) is
   begin
      if ( rising_edge(clk) ) then
         if    ( rst = '1' ) then
            r <= REG_INIT_C;
         elsif ( cen = '1' ) then
            r <= rin after TPD_G;
         end if;
      end if;
   end process P_SEQ;

   allD <= allDon and strb;
   avgD <= avgDon and strb;
   actv <= r.actv and strb;
   init <= r.init;
   smaj <= r.cnfg.sevr(1);
   smin <= r.cnfg.sevr(0);
   rate <= r.cnfg.rate;
   slot <= r.cnfg.slot;
end architecture TPGMiniEdefImpl;
