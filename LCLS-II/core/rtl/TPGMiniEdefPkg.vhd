library ieee;
use ieee.std_logic_1164.all;

use work.StdRtlPkg.all;

package TPGMiniEdefPkg is

   --subtype EdefNavgType is natural range 0 to 255;
   --subtype EdefNsmpType is natural range 0 to 2800;
   --subtype EdefType     is natural range 0 to 15;
   --subtype EdefTS       is natural range 0 to 5;
   subtype EdefNavgType is slv( 7 downto 0);
   subtype EdefNsmpType is slv(11 downto 0);
   subtype EdefType     is slv( 3 downto 0);
   subtype EdefTSType   is slv( 2 downto 0);
   subtype EdefRateType is slv( 2 downto 0);
   subtype EdefSevrType is slv( 1 downto 0);

   constant EDEF_NUM_BITS_C : natural :=   EdefNavgType'length
                                         + EdefNsmpType'length
                                         + EdefType'length
                                         + EdefTSType'length
                                         + EdefRateType'length
                                         + EdefSevrType'length;

   type TPGMiniEdefConfigType is record
      navg : EdefNavgType;
      nsmp : EdefNsmpType;
      edef : EdefType;
      slot : EdefTSType;
      rate : EdefRateType;
      sevr : EdefSevrType;
      wrEn : sl;
   end record TPGMiniEdefConfigType;

   constant TPG_MINI_EDEF_CONFIG_INIT_C : TPGMiniEdefConfigType := (
      navg => (others => '0'),
      nsmp => (others => '0'),
      edef => (others => '0'),
      slot => (others => '0'),
      rate => (others => '0'),
      sevr => (others => '0'),
      wrEn => '0'
   );

   function toSlv(cfg : TPGMiniEdefConfigType) return slv;
   function fromSlv(v : slv; wen : sl        ) return TPGMiniEdefConfigType;

end package TPGMiniEdefPkg;

package body TPGMiniEdefPkg is

   function toSlv(cfg : TPGMiniEdefConfigType) return slv is
      variable i : integer;
      variable v : slv(EDEF_NUM_BITS_C - 1 downto 0);
   begin
      i := 0;
      assignSlv( i, v, cfg.nsmp );
      assignSlv( i, v, cfg.rate );
      assignSlv( i, v, cfg.slot );
      assignSlv( i, v, cfg.sevr );
      assignSlv( i, v, cfg.edef );
      assignSlv( i, v, cfg.navg );
      return v; 
   end function toSlv;

   function fromSlv(v : slv; wen : sl) return TPGMiniEdefConfigType is
      variable i   : integer;
      variable cfg : TPGMiniEdefConfigType;
   begin
      i := 0;
      assignRecord( i, v, cfg.nsmp );
      assignRecord( i, v, cfg.rate );
      assignRecord( i, v, cfg.slot );
      assignRecord( i, v, cfg.sevr );
      assignRecord( i, v, cfg.edef );
      assignRecord( i, v, cfg.navg );
      cfg.wrEn := wen;
      return cfg; 
   end function fromSlv;


end package body TPGMiniEdefPkg;
