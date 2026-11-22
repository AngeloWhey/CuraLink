"""Consolidate saved primary LCSC responses against the complete Rev A BOM.

No network requests or purchases. Inventory is a dated snapshot. This report
keeps component sourcing separate from assembly eligibility and cell safety.
"""
from pathlib import Path
import collections
import csv
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'hardware/rev-a/procurement'
DATE = '2026-10-02'
EXTERNAL_MPNS = {'C6936300': 'FFC-0.5-18P-50mm', 'C19632326': '401020-55mah'}
SOURCES = [
    ROOT / f'procurement/stock-resistors-{DATE}.json',
    OUT / f'stock-capacitors-{DATE}.json',
    ROOT / f'procurement/stock-active-external-{DATE}.json',
]


def first(item, *keys, default=None):
    for key in keys:
        if key in item and item[key] is not None:
            return item[key]
    return default


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    bom = list(csv.DictReader((ROOT / 'hardware/rev-a/bom.csv').open(encoding='utf-8-sig')))
    groups = collections.defaultdict(list)
    for row in bom:
        assert row['LCSC'], f'Unassigned BOM row: {row}'
        groups[row['LCSC']].append(row)
    inventory = {}
    source_hashes = []
    for path in SOURCES:
        data = json.loads(path.read_text(encoding='utf-8'))
        source_hashes.append({'file': path.relative_to(ROOT).as_posix(),
                              'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        for item in first(data, 'records', 'items'):
            assert item['lcsc'] not in inventory, f'Duplicate audit SKU {item["lcsc"]}'
            inventory[item['lcsc']] = item
    assert set(groups) <= set(inventory), f'Missing inventory: {set(groups) - set(inventory)}'
    records = []
    for code, item in sorted(inventory.items(), key=lambda pair: int(pair[0][1:])):
        rows = groups.get(code, [])
        fit = sum(int(r['Quantity']) for r in rows if r['Populate'] == 'YES')
        opt = sum(int(r['Quantity']) for r in rows if r['Populate'] == 'NO')
        ext = 1 if code in EXTERNAL_MPNS else 0
        scope = 'REV_A_BOM' if rows else ('EXTERNAL_CELL_OR_CABLE' if ext else 'RETIRED_AUDITED_SKU')
        expected = (sorted({r['MPN'] for r in rows}) if rows else
                    ([EXTERNAL_MPNS[code]] if ext else [first(item,'mpn','expected_mpn')]))
        actual = first(item, 'product_model', 'actual_mpn', 'returned_mpn')
        exact = bool(actual and expected and expected == [actual])
        immediate = first(item, 'stock_immediate', 'stock_international_immediate',
                          default=(item.get('overseas_stock') or {}).get('shipImmediately'))
        total = first(item, 'stock_total', 'stock_number')
        minimum = first(item, 'minimum_order', 'minimum_order_quantity')
        multiple = item.get('order_multiple')
        sale = first(item, 'foreign_onsale', 'foreign_on_sale', 'is_foreign_onsale', default=False)
        display = first(item, 'foreign_display', 'is_foreign_display', default=False)

        def order(qty):
            if qty == 0:
                return 0
            if minimum is None or not multiple:
                return None
            return math.ceil(max(qty, minimum) / multiple) * multiple

        buy_fit = order(fit + ext)
        buy_all = order(fit + opt + ext)
        sufficient = bool(exact and sale and display and immediate is not None
                          and buy_all is not None and immediate >= buy_all)
        raw = first(item, 'raw_file', 'raw_response_file')
        assert raw and (ROOT / raw).exists(), f'Missing primary response {code}'
        tiers = [(p['quantity'], p['usd_per_piece']) for p in item.get('price_ladders_usd', [])]
        tiers += [(p['minimum_quantity'], p['unit_price_usd']) for p in item.get('usd_price_tiers', [])]
        if not tiers and item.get('unit_price_usd') is not None:
            tiers = [(first(item, 'price_basis_purchase_qty', default=minimum or 1), item['unit_price_usd'])]

        def price(qty):
            if qty == 0:
                return 0.0
            valid = [(n, p) for n, p in tiers if qty is not None and qty >= n]
            return sorted(valid)[-1][1] if valid else None

        price_fit = price(buy_fit)
        price_all = price(buy_all)
        records.append({
            'lcsc': code, 'expected_mpns': expected, 'actual_mpn': actual,
            'exact_mpn_match': exact, 'scope': scope,
            'populated_quantity': fit, 'optional_quantity': opt, 'external_quantity': ext,
            'references': ','.join(r['References'] for r in rows),
            'assembly': sorted({r.get('Assembly', 'OFFBOARD_MANUAL' if 'RT501' in r['References'] else 'PCB_SMT') for r in rows})
                         if rows else ['OFFBOARD_MANUAL'],
            'stock_total': total, 'stock_international_immediate': immediate,
            'foreign_onsale': sale, 'foreign_display': display,
            'minimum_order': minimum, 'order_multiple': multiple,
            'buy_quantity_populated': buy_fit, 'buy_quantity_including_optional': buy_all,
            'unit_price_usd_populated_order': price_fit,
            'minimum_order_cost_usd_populated': round(buy_fit * price_fit, 4) if buy_fit is not None and price_fit is not None else None,
            'minimum_order_cost_usd_including_optional': round(buy_all * price_all, 4) if buy_all is not None and price_all is not None else None,
            'checked_date': DATE, 'status': ('RETIRED_FROM_CURRENT_BOM' if scope=='RETIRED_AUDITED_SKU' else
                                          ('STOCK_SUFFICIENT_ONE_BOARD' if sufficient else 'UNCONFIRMED_DO_NOT_ORDER')),
            'source_url': first(item, 'source_url', 'product_url', default=f'https://www.lcsc.com/product-detail/{code}.html'),
            'primary_api_url': first(item, 'api_url', 'primary_api_url'),
            'raw_file': raw, 'raw_sha256': hashlib.sha256((ROOT / raw).read_bytes()).hexdigest(),
            'assembly_service_eligibility': 'NOT_VERIFIED',
        })
    covered = [r for r in records if r['scope'] == 'REV_A_BOM']
    stocked = [r for r in records if r['status'] == 'STOCK_SUFFICIENT_ONE_BOARD']
    report = {
        'checked_date': DATE, 'timezone': 'America/New_York', 'source_audits': source_hashes,
        'scope': 'Every current Rev A BOM SKU including optional parts and off-board NTC; external cell/cable and retired audited SKUs separately',
        'summary': {'bom_unique_skus': len(covered), 'bom_all_stock_sufficient': all(r['status'] == 'STOCK_SUFFICIENT_ONE_BOARD' for r in covered),
                    'total_current_skus_checked': sum(r['scope']!='RETIRED_AUDITED_SKU' for r in records),
                    'saved_audited_skus': len(records), 'retired_audited_skus': sum(r['scope']=='RETIRED_AUDITED_SKU' for r in records),
                    'stocked_current_skus': len(stocked),
                    'unconfirmed_skus': [r['lcsc'] for r in records if r['status']=='UNCONFIRMED_DO_NOT_ORDER'],
                    'populated_parts': sum(r['populated_quantity'] for r in records),
                    'optional_parts': sum(r['optional_quantity'] for r in records),
                    'known_minimum_order_cost_populated_usd': round(sum(r['minimum_order_cost_usd_populated'] or 0 for r in records), 2),
                    'known_minimum_order_cost_with_optional_usd': round(sum(r['minimum_order_cost_usd_including_optional'] or 0 for r in records), 2)},
        'limitations': ['Stock is not reserved and may change.', 'Foreign sale/display flags are not checkout/address/export approval.',
                       'One-board needs include DNP alternatives for stock qualification; do not populate incompatible alternatives together.',
                       'MOQ purchase cost is not fitted-parts cost or an assembly quote; excludes unconfirmed cell, freight, tax, PCB, assembly and feeder loss.',
                       'Copper test/wire pads are PCB artwork, not assembled connector components.',
                       'The cell-mounted NTC is an off-board manual component.',
                       'Inventory does not establish cell/protector compatibility, circuit performance or exact assembly-library eligibility.'],
        'records': records,
    }
    (OUT / f'stock-audit-{DATE}.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    columns = ['lcsc','actual_mpn','scope','populated_quantity','optional_quantity','external_quantity',
               'references','assembly','stock_international_immediate','minimum_order','order_multiple',
               'buy_quantity_populated','buy_quantity_including_optional','minimum_order_cost_usd_populated',
               'minimum_order_cost_usd_including_optional','checked_date','status','source_url','raw_file']
    with (OUT / f'stock-audit-{DATE}.csv').open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        for record in records:
            row = dict(record)
            row['assembly'] = ','.join(row['assembly'])
            writer.writerow(row)
    print(json.dumps(report['summary'], indent=2))


if __name__ == '__main__':
    main()
