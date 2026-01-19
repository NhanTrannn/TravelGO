import csv, os, re, sys
from pathlib import Path

CSV_PATH = Path(__file__).parent.parent / 'data' / 'hotels.csv'
BACKUP_PATH = CSV_PATH.with_suffix('.bak_images')

PATTERN_EXT = re.compile(r'\.(jpg|jpeg|png)$', re.IGNORECASE)

def build_url(hotel_id: str, filename: str) -> str:
    return f'https://i.vntrip.vn/600x600/smart/https://statics.vntrip.vn/data-v2/hotels/{hotel_id}/img_max/{filename}'

def main():
    if not CSV_PATH.exists():
        print(f'❌ CSV not found: {CSV_PATH}')
        return
    print(f'📂 Reading {CSV_PATH}')
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = list(csv.reader(f))
    header = reader[0]
    rows = reader[1:]

    # Determine column indexes
    col_index = {name: idx for idx, name in enumerate(header)}
    required = ['id','imageSrc']
    for r in required:
        if r not in col_index:
            print(f'❌ Missing column {r}'); return

    fixed = 0
    skipped = 0

    for r in rows:
        rid = r[col_index['id']]
        img = r[col_index['imageSrc']]
        if not rid.startswith('vntrip_'):
            skipped += 1
            continue
        if img.startswith('http'):
            skipped += 1
            continue
        if not PATTERN_EXT.search(img):
            skipped += 1
            continue
        hotel_id = rid.split('_',1)[1]
        r[col_index['imageSrc']] = build_url(hotel_id, img)
        fixed += 1

    # Backup original
    if not BACKUP_PATH.exists():
        with open(BACKUP_PATH, 'w', encoding='utf-8', newline='') as b:
            w = csv.writer(b)
            w.writerow(header); w.writerows(rows)
        print(f'🪣 Backup written: {BACKUP_PATH}')

    # Write updated
    with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(header); w.writerows(rows)

    print(f'✅ Image URL fix complete. Updated {fixed} rows, skipped {skipped}.')

if __name__ == '__main__':
    main()
