"""Read-only BOM capacitor inventory audit against the primary LCSC product API."""
import concurrent.futures
import csv
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
DATE = "2026-10-02"
RAW = OUT / f"stock-capacitors-{DATE}-raw"
ENDPOINT = "https://wmsc.lcsc.com/ftps/wm/product/detail?productCode={}"
RAW.mkdir(parents=True, exist_ok=True)

def get_part(code):
    request = urllib.request.Request(ENDPOINT.format(code), headers={
        "User-Agent": "Mozilla/5.0", "Origin": "https://www.lcsc.com"})
    with urllib.request.urlopen(request, timeout=45) as response:
        payload = response.read()
    fetched = dt.datetime.now(dt.timezone.utc).isoformat()
    parsed = json.loads(payload)
    if parsed.get("code") != 200 or not isinstance(parsed.get("result"), dict):
        raise ValueError(f"Unexpected API result for {code}: {parsed.get('code')}")
    path = RAW / f"{code}.json"
    path.write_bytes(payload)
    return parsed["result"], path, fetched, hashlib.sha256(payload).hexdigest()

def order_qty(qty, minimum, multiple):
    return int(math.ceil(max(qty, minimum) / multiple) * multiple) if qty else 0

def price_for_quantity(prices, qty):
    allowed = [p for p in prices if int(p.get("ladder", 0)) <= qty]
    if not allowed:
        return None
    entry = max(allowed, key=lambda p: int(p["ladder"]))
    return float(entry.get("usdPrice", entry.get("productPrice")))

def main():
    bom_path = ROOT / "hardware/rev-a/bom.csv"
    bom_data = bom_path.read_bytes()
    groups = {}
    with bom_path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            refs = row["References"].split(",")
            if not any(ref.startswith("C") and ref[1:].isdigit() for ref in refs):
                continue
            if not all(ref.startswith("C") and ref[1:].isdigit() for ref in refs):
                raise ValueError(f"Mixed capacitor and non-capacitor refs: {refs}")
            if int(row["Quantity"]) != len(refs):
                raise ValueError(f"BOM count/ref mismatch: {row}")
            code = row["LCSC"]
            entry = groups.setdefault(code, {"lcsc": code, "mpn": row["MPN"],
                "package": row["Package"], "bom_values": [], "populated_references": [],
                "dnp_references": [], "bom_tolerances": []})
            if entry["mpn"] != row["MPN"]:
                raise ValueError(f"Conflicting BOM MPN for {code}")
            entry["bom_values"].append(row["Value"])
            entry["bom_tolerances"].append(row["Tolerance"])
            entry["populated_references" if row["Populate"] == "YES" else "dnp_references"].extend(refs)
    results = {}
    errors = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(get_part, code): code for code in groups}
        for future in concurrent.futures.as_completed(futures):
            code = futures[future]
            try:
                results[code] = future.result()
            except Exception as exc:
                errors[code] = repr(exc)
    # A failed network request is retried once, without hiding an unverified result.
    for code in list(errors):
        try:
            results[code] = get_part(code)
            errors.pop(code)
        except Exception as exc:
            errors[code] = repr(exc)
    records = []
    for code in sorted(groups, key=lambda x: int(x[1:])):
        entry = groups[code]
        entry["bom_values"] = sorted(set(entry["bom_values"]))
        entry["bom_tolerances"] = sorted(set(entry["bom_tolerances"]))
        entry["one_board_populated_qty"] = len(entry["populated_references"])
        entry["one_board_dnp_qty"] = len(entry["dnp_references"])
        entry["one_board_populated_plus_dnp_qty"] = entry["one_board_populated_qty"] + entry["one_board_dnp_qty"]
        entry["checked_date"] = DATE
        entry["source_url"] = f"https://www.lcsc.com/product-detail/{code}.html"
        entry["api_url"] = ENDPOINT.format(code)
        if code in errors:
            entry.update({"status": "UNVERIFIED", "error": errors[code]})
            records.append(entry)
            continue
        part, path, timestamp, sha = results[code]
        minimum = int(part.get("minBuyNumber") or 1)
        multiple = int(part.get("split") or 1)
        quantity = order_qty(entry["one_board_populated_plus_dnp_qty"], minimum, multiple)
        stock = part.get("stockNumber")
        immediate = (part.get("overseasStockVO") or {}).get("shipImmediately")
        params = {p.get("paramNameEn"): p.get("paramValueEn") for p in part.get("paramVOList", [])}
        entry.update({"product_model": part.get("productModel"),
            "manufacturer": part.get("brandNameEn"), "stock_total": stock,
            "stock_immediate": immediate, "minimum_order": minimum,
            "order_multiple": multiple, "one_board_purchase_qty_populated": order_qty(entry["one_board_populated_qty"], minimum, multiple),
            "one_board_purchase_qty_populated_plus_dnp": quantity,
            "foreign_onsale": part.get("isForeignOnsale"),
            "foreign_display": part.get("isForeignDisplay"),
            "unit_price_usd": price_for_quantity(part.get("productPriceList", []), quantity),
            "price_basis_purchase_qty": quantity, "lcsc_parameters": params,
            "description": part.get("productIntroEn"), "datasheet_url": part.get("pdfUrl"),
            "raw_file": path.relative_to(ROOT).as_posix(), "raw_sha256": sha,
            "fetched_utc": timestamp, "assembly_library_eligibility": "NOT_VERIFIED_BY_LCSC_INVENTORY_API"})
        if entry["product_model"] != entry["mpn"]:
            status = "MPN_MISMATCH"
        elif entry["foreign_onsale"] is not True or entry["foreign_display"] is not True:
            status = "NOT_FOREIGN_ORDERABLE"
        elif not isinstance(immediate, (int, float)):
            status = "UNVERIFIED_IMMEDIATE_STOCK"
        elif immediate == 0:
            status = "ZERO_IMMEDIATE_STOCK"
        elif immediate < quantity:
            status = "SHORT_IMMEDIATE_STOCK"
        else:
            status = "STOCK_SUFFICIENT"
        entry["status"] = status
        records.append(entry)
    report = {"checked_date": DATE, "timezone": "America/New_York",
        "scope": "Every unique capacitor LCSC SKU in the combined Rev A BOM, including DNP",
        "bom_path": bom_path.relative_to(ROOT).as_posix(), "bom_sha256": hashlib.sha256(bom_data).hexdigest(),
        "source": "Primary LCSC unauthenticated product-detail API; original raw responses saved",
        "qualification": "Exact BOM MPN, foreign orderable/displayed, immediate overseas inventory covers one-board populated plus DNP quantity rounded to minimum/order increment",
        "limitations": ["Stock snapshot is not a reservation", "LCSC inventory availability does not establish JLCPCB assembly-library eligibility", "Catalog capacitance/dielectric/tolerance/voltage metadata saved for review; PCB DC-bias and RF stress remain engineering validation"],
        "unique_capacitor_skus": len(records),
        "one_board_populated_capacitors": sum(r["one_board_populated_qty"] for r in records),
        "one_board_dnp_capacitors": sum(r["one_board_dnp_qty"] for r in records),
        "all_stock_sufficient": all(r["status"] == "STOCK_SUFFICIENT" for r in records),
        "records": records}
    output = OUT / f"stock-capacitors-{DATE}.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "unique_skus": len(records),
        "status_counts": {status: sum(r["status"] == status for r in records) for status in sorted({r["status"] for r in records})},
        "exceptions": [{"lcsc": r["lcsc"], "status": r["status"]} for r in records if r["status"] != "STOCK_SUFFICIENT"],
        "precision_10nF": next(r for r in records if r["lcsc"] == "C2167903")}, ensure_ascii=True))

if __name__ == "__main__":
    main()
