"""Read-only LCSC resistor inventory audit for the existing one-board BOM."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import argparse
import csv
import hashlib
import json
import math
import re
import time
import urllib.request


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', required=True, help='Client-local audit date, YYYY-MM-DD')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    bom = root / 'hardware/rev-a/bom.csv'
    raw_dir = root / 'procurement' / f'raw-resistors-{args.date}'
    raw_dir.mkdir(parents=True, exist_ok=True)
    groups = {}
    rows = list(csv.DictReader(bom.open(encoding='utf-8-sig', newline='')))
    for row in rows:
        refs = [ref for ref in row['References'].split(',') if re.fullmatch(r'R\d+', ref)]
        if not refs:
            continue
        code = row['LCSC']
        group = groups.setdefault(code, {
            'lcsc': code, 'expected_mpn': row['MPN'], 'package': row['Package'],
            'values': [], 'required_tolerances': [], 'populated_refs': [], 'dnp_refs': []
        })
        assert group['expected_mpn'] == row['MPN'], (code, 'inconsistent BOM model')
        group['values'].append(row['Value'])
        group['required_tolerances'].append(row['Tolerance'])
        group['populated_refs' if row['Populate'] == 'YES' else 'dnp_refs'].extend(refs)

    def check(group):
        code = group['lcsc']
        url = 'https://wmsc.lcsc.com/ftps/wm/product/detail?productCode=' + code
        group['source_url'] = 'https://www.lcsc.com/product-detail/' + code + '.html'
        group['api_url'] = url
        group['mpn'] = group['expected_mpn']
        group['checked_date'] = args.date
        group['pcb_populated_quantity'] = len(group['populated_refs'])
        group['pcb_dnp_quantity'] = len(group['dnp_refs'])
        group['pcb_quantity_if_all_options_fitted'] = len(group['populated_refs']) + len(group['dnp_refs'])
        group['values'] = sorted(set(group['values']))
        group['required_tolerances'] = sorted(set(group['required_tolerances']))
        data = None
        for attempt in range(3):
            try:
                request = urllib.request.Request(url, headers={
                    'User-Agent': 'Mozilla/5.0', 'Origin': 'https://www.lcsc.com',
                    'Accept': 'application/json'
                })
                with urllib.request.urlopen(request, timeout=25) as response:
                    body = response.read()
                    group['server_response_date'] = response.headers.get('Date')
                data = json.loads(body)
                (raw_dir / (code + '.json')).write_bytes(body)
                group['raw_response_file'] = str((raw_dir / (code + '.json')).relative_to(root)).replace('\\', '/')
                group['raw_file'] = group['raw_response_file']
                if data.get('code') != 200 or not data.get('result'):
                    raise ValueError('LCSC returned no valid product result')
                break
            except Exception as error:
                group['error'] = repr(error)
                if attempt < 2:
                    time.sleep(0.5 * (attempt + 1))
        if not data or data.get('code') != 200 or not data.get('result'):
            group['status'] = 'UNVERIFIED_API_ERROR'
            return group
        group.pop('error', None)
        item = data['result']
        group['returned_lcsc'] = item.get('productCode')
        group['returned_mpn'] = item.get('productModel')
        group['product_model'] = item.get('productModel')
        group['returned_package'] = item.get('encapStandard')
        group['manufacturer'] = item.get('brandNameEn')
        group['description'] = item.get('productIntroEn') or item.get('productNameEn')
        group['exact_identity_match'] = item.get('productCode') == code and item.get('productModel', '').casefold() == group['expected_mpn'].casefold()
        group['stock_total'] = item.get('stockNumber')
        group['stock_international_immediate'] = (item.get('overseasStockVO') or {}).get('shipImmediately')
        group['stock_immediate'] = group['stock_international_immediate']
        group['stock_international_total'] = (item.get('overseasStockVO') or {}).get('total')
        group['minimum_order'] = item.get('minBuyNumber')
        group['order_multiple'] = item.get('split')
        group['foreign_on_sale'] = item.get('isForeignOnsale')
        group['foreign_onsale'] = group['foreign_on_sale']
        group['foreign_display'] = item.get('isForeignDisplay')
        group['pre_sale'] = item.get('isPreSale')
        group['third_party_stock'] = item.get('hasThirdPartyStock')
        group['datasheet'] = item.get('pdfUrl')
        group['price_ladders_usd'] = [
            {'quantity': price.get('ladder'), 'usd_per_piece': price.get('usdPrice')}
            for price in (item.get('productPriceList') or [])
        ]
        multiple = group['order_multiple'] or 1
        minimum = group['minimum_order'] or 1
        group['purchase_quantity_populated_only'] = (math.ceil(max(group['pcb_populated_quantity'], minimum) / multiple) * multiple) if group['pcb_populated_quantity'] else 0
        group['purchase_quantity_including_dnp'] = math.ceil(max(group['pcb_quantity_if_all_options_fitted'], minimum) / multiple) * multiple
        target = group['purchase_quantity_including_dnp']
        eligible_prices = [price for price in group['price_ladders_usd'] if (price['quantity'] or 0) <= target and price['usd_per_piece'] is not None]
        group['unit_price_usd'] = max(eligible_prices, key=lambda price: price['quantity'])['usd_per_piece'] if eligible_prices else None
        if not group['exact_identity_match']:
            group['status'] = 'IDENTITY_MISMATCH'
        elif group['foreign_on_sale'] is not True or group['foreign_display'] is not True or group['pre_sale'] is True:
            group['status'] = 'ORDERABILITY_REQUIRES_REVIEW'
        elif group['stock_total'] is None:
            group['status'] = 'UNVERIFIED_STOCK'
        elif group['stock_total'] == 0:
            group['status'] = 'OUT_OF_STOCK'
        elif group['stock_total'] < target:
            group['status'] = 'INSUFFICIENT_FOR_MINIMUM_ORDER'
        elif group['stock_international_immediate'] is None:
            group['status'] = 'STOCKED_IMMEDIATE_SHIPPING_UNVERIFIED'
        elif group['stock_international_immediate'] < target:
            group['status'] = 'STOCKED_SHIPPING_DELAY_OR_SHORTFALL'
        else:
            group['status'] = 'IN_STOCK_ONE_BOARD_INCLUDING_DNP'
        return group

    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        for future in as_completed([executor.submit(check, group) for group in groups.values()]):
            result = future.result()
            results.append(result)
            print(result['lcsc'], result['status'], 'stock', result.get('stock_total'), 'order', result.get('purchase_quantity_including_dnp'), flush=True)
    results.sort(key=lambda result: (int(result['lcsc'][1:]) if re.fullmatch(r'C\d+', result['lcsc']) else -1))
    report = {
        'audit_date': args.date, 'date_source': 'Client environment America/New_York',
        'bom_source': 'hardware/rev-a/bom.csv', 'bom_sha256': hashlib.sha256(bom.read_bytes()).hexdigest(),
        'scope': 'All PCB BOM refs matching R followed by digits, including DNP; one-board quantities',
        'source_method': 'Unauthenticated read-only LCSC public product detail API; exact code and model identity required',
        'not_verified': ['Stock reservation', 'JLCPCB assembly-library eligibility', 'Checkout/export/address eligibility', 'Placement feeder wastage'],
        'unique_skus': len(results), 'populated_resistors': sum(result['pcb_populated_quantity'] for result in results),
        'dnp_resistors': sum(result['pcb_dnp_quantity'] for result in results),
        'all_stocked_for_one_board_including_dnp': all(result['status'] == 'IN_STOCK_ONE_BOARD_INCLUDING_DNP' for result in results),
        'records': results
    }
    target = root / 'procurement' / f'stock-resistors-{args.date}.json'
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Saved', target, 'all stocked:', report['all_stocked_for_one_board_including_dnp'])


if __name__ == '__main__':
    main()
