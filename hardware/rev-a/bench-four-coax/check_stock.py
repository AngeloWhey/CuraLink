"""Check the fitted four-input BOM and bench leads against LCSC and JLC's public catalogs."""
import csv
import datetime
import json
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen

OUT = Path(__file__).resolve().parent
LCSC = "https://wmsc.lcsc.com/ftps/wm/product/detail?productCode="
JLC = "https://cart.jlcpcb.com/shoppingCart/smtGood/getComponentDetail?componentCode="


def query(url):
    req = Request(url,headers={"User-Agent":"Mozilla/5.0"})
    for attempt in range(3):
        try:
            with urlopen(req,timeout=15) as response:
                return json.load(response)
        except (TimeoutError,OSError):
            if attempt==2:
                raise


def check(item):
    code, use=item
    d=query(LCSC+code)["result"]
    if not d or d["productModel"].casefold() != use["mpn"].casefold():
        raise ValueError((code,use["mpn"],d and d.get("productModel")))
    j=query(JLC+code).get("data") or {}
    if j and j.get("componentModelEn","").casefold() != use["mpn"].casefold():
        raise ValueError((code,use["mpn"],j.get("componentModelEn")))
    return {"LCSC":code,"MPN":use["mpn"],"Fitted":use["fit"],"DNP":use["dnp"],
            "Bench leads":use["leads"],"Package":d["encapStandard"],
            "LCSC ships immediately":d["overseasStockVO"]["shipImmediately"],
            "LCSC MOQ":d["minBuyNumber"],"LCSC multiple":d["split"],
            "JLC stockCount":j.get("stockCount"),"JLC source":j.get("componentSource"),
            "JLC assembly process":j.get("assemblyProcess"),"LCSC product URL":"https://www.lcsc.com/product-detail/"+code+".html",
            "LCSC inventory URL":LCSC+code,"JLC inventory URL":JLC+code}


def main():
    groups=defaultdict(lambda: {"fit":0,"dnp":0,"leads":0})
    with (OUT/"assembly-bom.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            code=row["LCSC"]
            if not code:
                assert row["Populate"]=="DNP"
                continue
            u=groups[code]
            assert "mpn" not in u or u["mpn"]==row["MPN"]
            u["mpn"]=row["MPN"]
            u[row["Populate"].lower()]+=int(row["Quantity"])
    groups["C784403"].update(mpn="BWIPX1-SMA-1.13L100",leads=4)
    with ThreadPoolExecutor(max_workers=6) as pool:
        rows=list(pool.map(check,sorted(groups.items())))
    # Pad-number equality alone cannot spot a 0603 on a 0402 land.
    packages={r["LCSC"]:r["Package"] for r in rows}
    native=ET.parse(OUT/"curalink-four-coax.net.xml")
    for p in native.findall("./components/comp"):
        fp=p.findtext("footprint") or ""
        passive=re.match(r"CuraLink:[RCL]_(0402|0603|0805|1206)_",fp)
        fields={f.get("name"):f.text for f in p.findall("./fields/field")}
        code=fields.get("LCSC")
        if passive and code:
            assert packages[code]==passive[1],(p.get("ref"),code,packages[code],fp)
    now=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    dated="stock-"+now[:10]+".csv"
    with (OUT/dated).open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=["Checked UTC",*rows[0]])
        w.writeheader()
        w.writerows(dict(r,**{"Checked UTC":now}) for r in rows)
    shorts=[r["MPN"] for r in rows if r["LCSC ships immediately"]<r["Fitted"]+r["Bench leads"]]
    print(f"{len(rows)} codes checked; below single-unit demand: {shorts}")


if __name__=="__main__":
    main()
