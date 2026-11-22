"""Read-only live LCSC inventory audit for non-R/C Rev A parts and external items."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
import csv
import hashlib
import json
import math
import re
import time
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-10-02"
OUT = ROOT / "procurement"
RAW = OUT / ("raw-active-external-" + DATE)
RAW.mkdir(parents=True, exist_ok=True)
API = "https://wmsc.lcsc.com/ftps/wm/product/detail?productCode="


def utc_now():
    return datetime.now(timezone.utc).isoformat()


items = {}
excluded = []
with (ROOT / "hardware/rev-a/bom.csv").open(encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        refs = row["References"].split(",")
        if all(re.match(r"^[RC][0-9]", ref) for ref in refs):
            continue
        sku = row["LCSC"].strip()
        if not sku:
            excluded.append(row)
            continue
        item = items.setdefault(sku, {
            "lcsc": sku, "requested_mpns": [], "references_populated": [],
            "references_dnp": [], "board_quantity_populated": 0,
            "board_quantity_dnp": 0, "external_quantity": 0, "assembly": [],
            "package_requested": [], "scope": "REV_A_BOM_NON_RC",
        })
        if row["MPN"] not in item["requested_mpns"]:
            item["requested_mpns"].append(row["MPN"])
        if row["Assembly"] not in item["assembly"]:
            item["assembly"].append(row["Assembly"])
        if row["Package"] not in item["package_requested"]:
            item["package_requested"].append(row["Package"])
        pop = row["Populate"] == "YES"
        item["references_populated" if pop else "references_dnp"].extend(refs)
        item["board_quantity_populated" if pop else "board_quantity_dnp"] += int(row["Quantity"])

for sku, mpn, desc in [
    ("C19632326", "401020-55mah", "Accepted working bare LiPo cell; protected-pack compatibility not qualified"),
    ("C6936300", None, "18-position FFC cable for J301; exact catalogue MPN and geometry to verify"),
]:
    items[sku] = {
        "lcsc": sku, "requested_mpns": [mpn] if mpn else [],
        "references_populated": [], "references_dnp": [],
        "board_quantity_populated": 0, "board_quantity_dnp": 0,
        "external_quantity": 1, "assembly": ["OFFBOARD_MANUAL"],
        "package_requested": [], "scope": "EXTERNAL_ACCEPTED_ITEM",
        "note": desc,
    }


def fetch(sku, item):
    url = API + sku
    attempts = []
    for attempt in range(3):
        stamp = utc_now()
        try:
            request = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0", "Origin": "https://www.lcsc.com",
                "Cache-Control": "no-cache", "Accept": "application/json",
            })
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read()
                http_status = response.status
                response_headers = dict(response.headers)
            raw_file = RAW / (sku + ".json")
            raw_file.write_bytes(body)
            metadata = {
                "retrieved_at_utc": stamp, "url": url, "http_status": http_status,
                "headers": response_headers, "raw_sha256": hashlib.sha256(body).hexdigest(),
                "raw_file": str(raw_file.relative_to(ROOT)).replace("\\", "/"),
            }
            (RAW / (sku + "-metadata.json")).write_text(json.dumps(metadata, indent=2), encoding="utf-8")
            payload = json.loads(body)
            product = payload.get("result") or {}
            if not product or not payload.get("ok"):
                raise ValueError("API returned no successful product record: " + str(payload.get("msg")))
            overseas = product.get("overseasStockVO") or {}
            minimum = int(product.get("minBuyNumber") or 1)
            split = int(product.get("split") or 1)
            populated = item["board_quantity_populated"] + item["external_quantity"]
            all_qty = populated + item["board_quantity_dnp"]
            buy = max(minimum, math.ceil(populated / split) * split) if populated else 0
            buy_with_dnp = max(minimum, math.ceil(all_qty / split) * split)
            tiers = sorted(product.get("productPriceList") or [], key=lambda t: t["ladder"])

            def cost(qty):
                eligible = [t for t in tiers if t["ladder"] <= qty]
                if not qty or not eligible:
                    return None
                unit = eligible[-1].get("usdPrice")
                return {"quantity": qty, "unit_price_usd": unit,
                        "extended_usd": round(qty * unit, 6) if unit is not None else None}

            stock = product.get("stockNumber")
            immediate = overseas.get("shipImmediately")
            foreign_sale = product.get("isForeignOnsale")
            foreign_display = product.get("isForeignDisplay")
            requested = item["requested_mpns"]
            actual = product.get("productModel")
            exact = not requested or actual in requested
            if not exact:
                status = "MPN_MISMATCH_REVIEW"
            elif foreign_sale is False or foreign_display is False:
                status = "OVERSEAS_NOT_ORDERABLE"
            elif immediate is None:
                status = "OVERSEAS_INVENTORY_UNAVAILABLE"
            elif immediate < buy_with_dnp:
                status = "OUT_OF_STOCK" if immediate == 0 else "INSUFFICIENT_STOCK"
            else:
                status = "IN_STOCK_OVERSEAS"
            item.update({
                "retrieved_at_utc": stamp,
                "actual_mpn": actual, "mpn_exact_match": exact,
                "manufacturer": product.get("brandNameEn"),
                "product_description": product.get("productNameEn"),
                "package_actual": product.get("encapStandard"),
                "stock_number": stock, "overseas_stock": overseas,
                "domestic_stock": product.get("domesticStockVO"),
                "is_foreign_onsale": foreign_sale, "is_foreign_display": foreign_display,
                "minimum_order_quantity": minimum, "order_multiple": split,
                "buy_quantity_populated_only": buy,
                "buy_quantity_including_dnp": buy_with_dnp,
                "usd_price_tiers": [{"minimum_quantity": t["ladder"], "unit_price_usd": t.get("usdPrice")} for t in tiers],
                "populated_order_cost": cost(buy), "order_cost_including_dnp": cost(buy_with_dnp),
                "stock_status": status, "product_url": "https://www.lcsc.com/product-detail/" + sku + ".html",
                "datasheet_url": product.get("pdfUrl"),
                "primary_api_url": url, "raw_file": metadata["raw_file"],
                "param_vo_list": product.get("paramVOList"), "attempt_errors": attempts,
            })
            return item
        except Exception as error:
            attempts.append({"attempt": attempt + 1, "utc": stamp, "error": str(error)})
            if attempt < 2:
                time.sleep(1 + attempt)
    unavailable = (RAW / (sku + ".json")).exists() and all("no successful product record" in a["error"] for a in attempts)
    item.update({"stock_status": "CATALOG_RECORD_UNAVAILABLE" if unavailable else "FETCH_FAILED", "attempt_errors": attempts, "primary_api_url": url})
    return item


records = []
with ThreadPoolExecutor(max_workers=6) as pool:
    jobs = [pool.submit(fetch, sku, item) for sku, item in sorted(items.items())]
    for job in as_completed(jobs):
        item = job.result()
        records.append(item)
        print(item["lcsc"], item.get("actual_mpn"), item["stock_status"], item.get("overseas_stock"), flush=True)
records.sort(key=lambda i: i["lcsc"])
summary = {
    "unique_skus": len(records),
    "status_counts": {status: sum(i["stock_status"] == status for i in records) for status in sorted({i["stock_status"] for i in records})},
    "populated_quantity_bom": sum(i["board_quantity_populated"] for i in records),
    "dnp_quantity_bom": sum(i["board_quantity_dnp"] for i in records),
    "external_quantity": sum(i["external_quantity"] for i in records),
    "minimum_order_cost_populated_usd": round(sum((i.get("populated_order_cost") or {}).get("extended_usd", 0) or 0 for i in records), 4),
    "minimum_order_cost_including_dnp_usd": round(sum((i.get("order_cost_including_dnp") or {}).get("extended_usd", 0) or 0 for i in records), 4),
}
report = {
    "audit_date_local": DATE, "timezone": "America/New_York",
    "completed_at_utc": utc_now(), "source_bom": "hardware/rev-a/bom.csv",
    "source_bom_sha256": hashlib.sha256((ROOT / "hardware/rev-a/bom.csv").read_bytes()).hexdigest(),
    "scope": "Every unique non-R/C Rev A BOM SKU, including DNP, plus accepted cell and FFC cable",
    "inventory_meaning": "LCSC overseas immediate stock, exact MPN and overseas sale/display flags checked against one-board needs and minimum order quantity; stock is a snapshot, not a reservation or assembly allocation.",
    "cost_basis": "Minimum-order USD line costs, excludes freight, tax, assembly, feeder losses, PCB and R/C items. DNP order shown separately.",
    "summary": summary, "items": records, "excluded_nonpurchased_pads": excluded,
}
target = OUT / ("stock-active-external-" + DATE + ".json")
target.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(summary, indent=2))
print(target)
