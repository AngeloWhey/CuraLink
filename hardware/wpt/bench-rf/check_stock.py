"""Check the exact RF parts and order-minimum quantities for one TX/RX pair."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime, timezone
import json
from math import ceil
from pathlib import Path
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent


def lookup(record):
    code, mpn, quantity = record
    url = "https://wmsc.lcsc.com/ftps/wm/product/detail?productCode=" + code
    req = Request(url, headers={"User-Agent":"Mozilla/5.0", "Origin":"https://www.lcsc.com"})
    with urlopen(req, timeout=20) as response:
        part = json.load(response)["result"]
    sku_ok = part["productModel"] == mpn
    stock = part["overseasStockVO"]["shipImmediately"]
    multiple = part.get("split") or 1
    order = ceil(max(quantity,part.get("minBuyNumber") or 1)/multiple)*multiple
    return dict(lcsc=code, mpn=mpn, matched=sku_ok, required=quantity, order=order, immediate=stock,
                sufficient=sku_ok and stock >= order, source=url, checked_utc=datetime.now(timezone.utc).isoformat())


if __name__ == "__main__":
    with (HERE/"population.csv").open(newline="") as f:
        counts = Counter((p["lcsc"],p["mpn"]) for p in csv.DictReader(f) if p["lcsc"])
    with ThreadPoolExecutor(max_workers=4) as workers:
        records = list(workers.map(lookup, ((c,m,n) for (c,m),n in counts.items())))
    (HERE/"stock.json").write_text(json.dumps(records,indent=2)+"\n")
    for item in records:
        print(item["lcsc"], item["mpn"], item["immediate"], item["sufficient"])
