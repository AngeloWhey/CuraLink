"""Price one fitted electronics board, one TX/RX pair and four bench cables."""
from collections import Counter
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
import csv
import json
from math import ceil
from pathlib import Path
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def fitted_quantities(low_capacitance):
    quantities = Counter()
    board = ROOT / "hardware/rev-a" / ("bench-four-coax-low-c" if low_capacitance else "bench-four-coax")
    with (board / "stock-2026-11-22.csv").open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            qty = int(row["Fitted"]) + int(row["Bench leads"])
            if qty:
                quantities[row["LCSC"], row["MPN"]] += qty
    with (ROOT / "hardware/wpt/bench-rf/population.csv").open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row["lcsc"]:
                quantities[row["lcsc"], row["mpn"]] += 1
    return quantities


def price(item):
    (code, mpn), qty = item
    url = "https://wmsc.lcsc.com/ftps/wm/product/detail?productCode=" + code
    req = Request(url, headers={"User-Agent": "Mozilla/5.0", "Origin": "https://www.lcsc.com"})
    with urlopen(req, timeout=25) as response:
        part = json.load(response)["result"]
    if part["productModel"].casefold() != mpn.casefold():
        raise ValueError((code, mpn, part["productModel"]))
    multiple = int(part.get("split") or 1)
    order = ceil(max(qty, part["minBuyNumber"] or 1) / multiple) * multiple
    tiers = [t for t in part["productPriceList"] if t["ladder"] <= order and t["usdPrice"] is not None]
    unit = Decimal(str(max(tiers, key=lambda t: t["ladder"])["usdPrice"]))
    return {"lcsc": code, "mpn": mpn, "required": qty, "order_qty": order,
            "in_stock": part["overseasStockVO"]["shipImmediately"], "unit_USD": str(unit),
            "extended_USD": str(unit*order), "source": url}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--low-c", action="store_true")
    args = parser.parse_args()
    with ThreadPoolExecutor(max_workers=5) as pool:
        rows = list(pool.map(price, sorted(fitted_quantities(args.low_c).items())))
    name = "low-c-basket.csv" if args.low_c else "basket.csv"
    with (HERE / name).open("w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    print(datetime.now(timezone.utc).isoformat(), len(rows), sum(Decimal(r["extended_USD"]) for r in rows),
          "sufficient", all(r["order_qty"] <= r["in_stock"] for r in rows))
