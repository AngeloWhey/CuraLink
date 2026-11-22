"""Construct a native four-terminal rectifier and visible fixed-coil ADS bench.

Build in a private copy of the small library, then publish only the two new
cell directories after generating the hierarchical netlist. Existing cells
are never opened for editing. Run with ADS's Python.
"""
from pathlib import Path
import hashlib
import json
import math
import os
import shutil
import sys
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
WS=ROOT/"ads/MyWorkspace_wrk"
SDK=Path(os.environ.get("CURALINK_ADS_ROOT",r"C:\Program Files\Keysight\ADS2026_Update2"))
os.environ.setdefault("HPEESOF_DIR",str(SDK))
from keysight.ads import de
from keysight.ads.de import db_uu as db
from keysight.ads.de.experimental.generate_symbol import SymbolGenerator

LIB="MyLibrary_lib"
TOP="CuraLink_RX_BAS4002A_HB"
PART="BAS4002A_SOT143"
F=13.56e6
RFLIB="ads_rflib"


def hashes():
    return {p.relative_to(WS).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (WS/LIB).rglob("sch.oa") if not any(s in p.as_posix() for s in ("%B%A%S4002","%Cura%Link_%R%X"))}


def item(d,lib,cell,name,xy,values=None,angle=0):
    x=d.add_instance(f"{lib}:{cell}:symbol",xy,name=name,angle=angle)
    for k,v in (values or {}).items():
        x.parameters[k].value=v
    x.update_item_annotation()
    return x


def point(inst,pin):
    pt=inst.inst_term_numbered(pin).inst_pins[0].snap_point
    return (pt.x,pt.y)


def connect(d,inst,pin,net):
    xy=point(inst,pin)
    if net=="0":
        d.add_instance("ads_rflib:GROUND:symbol",xy)
    else:
        inst.inst_term_numbered(pin).add_label(net,(xy[0],xy[1]+.19))


def two(d,kind,name,xy,left,right,values=None,angle=0):
    x=item(d,RFLIB,kind,name,xy,values,angle)
    connect(d,x,1,left);connect(d,x,2,right)
    return x


def wire(d,a,ap,b,bp):
    p=point(a,ap);q=point(b,bp)
    if p==q: return
    mid=(q[0],p[1])
    d.add_wire([p,q] if mid in (p,q) else [p,mid,q])


def note(d,text,xy,h=.22):
    d.add_text(db.LayerId(228,237),text,xy,"Roboto",h)


def component(lib):
    design=db.create_schematic(f"{LIB}:{PART}:schematic")
    for index,(name,xy,angle) in enumerate([("DCM",(0,-5),180),("AC_A",(0,3),180),
                                           ("AC_B",(0,-1),180),("DCP",(14,1),0)],1):
        net=design.find_or_add_net(name)
        term=design.add_term(net,name,db.TermType.INPUT_OUTPUT)
        term.number=index
        assert term.number==index
        dot=design.add_dot(db.LayerId(231),xy)
        design.add_pin(term,dot,angle=angle)
    # Package pin resistance and inductance are explicit engineering sensitivities.
    for i,(n1,n2,xy) in enumerate([("DCM","P1",(1,-5)),("AC_A","P2",(1,3)),
                                   ("AC_B","P3",(1,-1)),("P4","DCP",(10,1))],1):
        lead=two(design,"L",f"Lead{i}",xy,n1,n2,{"L":"1 nH","R":"8 mOhm","Noise":"no"})
        if i<4: design.add_wire([(0,xy[1]),point(lead,1)])
        else: design.add_wire([point(lead,2),(14,1)])
    item(design,RFLIB,"Diode_Model","BASFIT",(0,-9),{
        "Is":"1.16603251135e-10 A","N":"0.8043801630717","Rs":"1.252429491587 Ohm",
        "Cjo":"5.896543968227 pF","Vj":"0.65 V","M":"0.5","Fc":"0.5","Tnom":"25","Imax":"100"})
    for i,n1,n2,xy in [(1,"P1","P2",(4,3)),(2,"P2","P4",(8,3)),(3,"P1","P3",(4,-1)),(4,"P3","P4",(8,-1))]:
        two(design,"Diode",f"D{i}",xy,n1,n2,{"Model":"BASFIT","Temp":"25","Noise":"no"})
    note(design,"BAS4002A | ONE SOT-143 PACKAGE | Typical junction fit at 25 C", (0,6),.34)
    note(design,"1 = DC negative    2, 3 = floating RF inputs    4 = DC positive\n"
                "Each lead: assumed 1 nH / 8 mOhm. Leakage, recovery and temperature remain unqualified.",(4,-5.4))
    design.save_design()
    sym=db.create_symbol(f"{LIB}:{PART}:symbol")
    generator=SymbolGenerator(sym,design,.5,.65)
    generator.pin_shape="square";generator.is_use_pin_net_text_label=True
    generator.generate_symbol();sym.save_design()


def receiver(lib):
    d=db.create_schematic(f"{LIB}:{TOP}:schematic")
    note(d,"CuraLink | 13.56 MHz fixed-coil link and packaged receiver", (0,7),.39)
    note(d,"25 dBm into 50 ohm available | 10 mm published separation | 24 mA raw load | 25 C | HB order 31",(0,6.2))
    gen=item(d,"ads_sources","P_1Tone","TXsource",(0,0),{"Num":"1","Z":"50 Ohm",
             "P":"polar(dbmtow(Pin_dBm),0)","Freq":"13.56 MHz","Noise":"no"})
    connect(d,gen,1,"GEN");connect(d,gen,2,"0")
    var=item(d,"ads_datacmps","VAR","Settings",(0,-8))
    for name,value in {"Pin_dBm":"25","Iload_mA":"24","TXseries_pF":"60","TXshunt_pF":"375",
                       "RXseries_pF":"1000","RXshunt_pF":"680","Cap_Q":"500","Carrier_Hz":"13.56e6"}.items():
        var.vars[name]=value
    var.update_item_annotation()
    item(d,"ads_simulation","HarmonicBalance","HB1",(21,-8),
         {"Freq":["13.56 MHz"],"Order":["31"],"MaxOrder":"31"})
    amps=item(d,"ads_simulation","MeasEqn","Results",(9,-8),{"Meas":[
        "Vraw_DC=real(mix(RAW,{0}))","Praw_mW=1000*Vraw_DC*real(mix(IDC.i,{0}))",
        "eta_available=(Praw_mW/1000)/dbmtow(Pin_dBm)",
        "Z_RX_fund=(mix(RXPLUS,{1})-mix(AC2,{1}))/mix(PRX.i,{1})"]})
    txprobe=two(d,"I_Probe","PTX",(2,2),"GEN","TX",{"SaveCurrent":"yes"})
    wire(d,gen,1,txprobe,1)
    # The R in each capacitor branch is its explicit ESR at the carrier.
    def cap_pair(rid,cid,loc1,loc2,net1,mid,net2,varname,angle=0):
        factor=f"1/(2*pi*Carrier_Hz*{varname}*1e-12*Cap_Q)"
        r=two(d,"R",rid,loc1,net1,mid,{"R":factor,"Noise":"no"},angle)
        c=two(d,"C",cid,loc2,mid,net2,{"C":f"{varname}*1e-12"},angle)
        wire(d,r,2,c,1)
        return r,c
    rt,cts=cap_pair("RTS","CTS",(4,2),(6,2),"TX","TS","TXCOIL","TXseries_pF")
    rh,cth=cap_pair("RTH","CTH",(3,-.5),(3,-3),"TX","TH","0","TXshunt_pF",-90)
    wire(d,txprobe,2,rt,1)
    lt=two(d,"L","L1",(9,2),"TXCOIL","0",{"L":"2.49 uH","R":"1.8 Ohm","Noise":"no"},-90)
    wire(d,cts,2,lt,1)
    lr=two(d,"L","L2",(12,1),"AC2","RXPLUS",{"L":"0.330 uH","R":"0.399 Ohm","Noise":"no"},90)
    item(d,RFLIB,"Mutual","Link",(9,4.7),{"K":"0.0662","Inductor1":'"L1"',"Inductor2":'"L2"'})
    pr=two(d,"I_Probe","PRX",(14,2),"RXPLUS","RX",{"SaveCurrent":"yes"})
    wire(d,lr,2,pr,1)
    rr,crs=cap_pair("RRS","CRS",(16,2),(18,2),"RX","RS","AC1","RXseries_pF")
    wire(d,pr,2,rr,1)
    rrh,crh=cap_pair("RRH","CRH",(20,-.5),(20,-3),"AC1","RH","AC2","RXshunt_pF",-90)
    pkg=item(d,LIB,PART,"U_RX",(24,2))
    pinmap={"DCM":1,"AC_A":2,"AC_B":3,"DCP":4}
    assert {t.term_number for t in pkg.inst_terms}==set(pinmap.values())
    for name,net in {"DCM":"0","AC_A":"AC1","AC_B":"AC2","DCP":"RAW"}.items():
        connect(d,pkg,pinmap[name],net)
    # Net labels keep the differential RX return independent from GND.
    lres=two(d,"L","LRES",(29,.5),"RAW","RESC",{"L":"0.7 nH","R":"50 mOhm","Noise":"no"},-90)
    cres=two(d,"C","CRES",(29,-2.5),"RESC","0",{"C":"1 uF"},-90)
    wire(d,lres,2,cres,1)
    iout=two(d,"I_Probe","IDC",(30,2),"RAW","OUT",{"SaveCurrent":"yes"})
    load=item(d,"ads_datacmps","SDD1P","Load",(33,2),{"SDD":[["1","0","Iload_mA*1e-3*tanh(_v1/.2)"]]},-90)
    connect(d,load,1,"OUT");connect(d,load,2,"0");wire(d,iout,2,load,1)
    note(d,"Double-click U_RX for the four fitted junctions and four package leads.\n"
           "This loaded RF fixture ends at RAW before regulation. For TPS70950 startup and TVS stress use the archived standalone decks.",(22,-5))
    text=d.generate_netlist()
    for name in ["PRX","U_RX","L1","L2","RTS","RT H".replace(" ",""),"RRS","RRH","CRES","Load"]:
        assert name in text,name
    d.save_design()
    return text


def main():
    before=hashes()
    assert len(before)==5,before
    with tempfile.TemporaryDirectory(prefix="curalink_native_ads_",ignore_cleanup_errors=True) as tmp:
        stage=Path(tmp)/"Receiver_wrk";stage.mkdir()
        shutil.copy2(WS/"lib.defs",stage/"lib.defs")
        shutil.copytree(WS/LIB,stage/LIB,ignore=shutil.ignore_patterns("*.cdslck","*.lck"))
        de.open_workspace(stage)
        library=de.get_open_library(LIB)
        assert not library.cell_exists(TOP) and not library.cell_exists(PART)
        try:
            component(library)
            text=receiver(library)
            folders={n:library.cell(n).view("schematic").path.parent.name for n in (PART,TOP)}
        finally:
            de.close_workspace()
            os.chdir(HERE)
        for n,folder in folders.items():
            target=WS/LIB/folder
            if target.exists(): raise FileExistsError(target)
            shutil.copytree(stage/LIB/folder,target,ignore=shutil.ignore_patterns("*.cdslck","*.lck"))
    # Open and netlist again from the published portable workspace.
    de.open_workspace(WS)
    top=db.open_design(f"{LIB}:{TOP}:schematic",de.db.DesignMode.READ_ONLY)
    fresh=top.generate_netlist()
    (HERE/"native-fresh-readback.ckt").write_text(fresh)
    (HERE/"creation-netlist.ckt").write_text(text)
    for name,digest in before.items():
        assert hashlib.sha256((WS/name).read_bytes()).hexdigest()==digest
    (HERE/"creation.json").write_text(json.dumps(dict(cells=folders,preceding_five_oa_sha256=before),indent=2)+"\n")
    print(folders)


if __name__=="__main__":
    main()
