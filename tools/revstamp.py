#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Revizyon Takip Sistemi - Otokodlama
- REV satırı ekler/günceller
- Gövde hash'ine göre değişikliği algılar
- 650 satır sınırı için uyarır
- "Parça" alanını 1/1 olarak bırakır; istenirse --part i/N ile geçersiz kılınır
"""
import argparse, hashlib, io, os, re, sys, datetime
HEADER_RE = re.compile(r'^\s*#\s*REV:\s*(\d+)\.(\d+)\s*\|\s*([0-9\-]{10})\s*\|\s*Hash:\s*([A-Za-z0-9]+)\s*\|\s*Parça:\s*(\d+)\/(\d+)\s*$')
COMMENT_PREFIXES = {
    '.py': '# ', '.sh': '# ', '.ps1': '# ', '.js': '// ', '.ts': '// ',
    '.css': '/* ', '.html': '{# ', '.htm': '{# ', '.vue': '<!-- ', '.json': '// ',
    '.md': '<!-- ', '.yml': '# ', '.yaml': '# ', '.ini': '; ', '.cfg': '; ',
}
COMMENT_SUFFIX = {
    '.css': ' */', '.html': ' #}', '.htm': ' #}', '.vue': ' -->', '.md': ' -->', '.json': '',
}

def detect_prefix_suffix(path):
    ext = os.path.splitext(path)[1].lower()
    prefix = COMMENT_PREFIXES.get(ext, '# ')
    suffix = COMMENT_SUFFIX.get(ext, '')
    return prefix, suffix

def strip_existing_header(lines):
    # İlk 5 satır içinde REV başlığı varsa ayıkla
    new_lines = []
    header_lines = []
    found = False
    for i, line in enumerate(lines[:5]):
        if HEADER_RE.match(line.strip()):
            header_lines.append(i)
            found = True
            break
    if found:
        # baştaki diğer açıklama satırını koru
        return lines[1:], True
    return lines, False

def compute_body_hash(text):
    h = hashlib.sha1(text.encode('utf-8')).hexdigest()
    return h[:8]

def read_file(path):
    with io.open(path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()

def write_file(path, text):
    with io.open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)

def format_header(prefix, suffix, rev_major, rev_minor, date_s, hash_s, part_s):
    base = f"REV: {rev_major}.{rev_minor} | {date_s} | Hash: {hash_s} | Parça: {part_s}"
    if suffix:
        return f"{prefix}{base}{suffix}\n"
    return f"{prefix}{base}\n"

def parse_existing_header(first_line):
    m = HEADER_RE.match(first_line.strip())
    if not m: return None
    return dict(major=int(m.group(1)), minor=int(m.group(2)),
                date=m.group(3), hash=m.group(4), part=f"{m.group(5)}/{m.group(6)}")

def process_file(path, bump_major=False, part_override=None, quiet=False):
    raw = read_file(path)
    lines = raw.splitlines(True)
    prefix, suffix = detect_prefix_suffix(path)

    # mevcut header’ı al
    existing = parse_existing_header(lines[0]) if lines else None

    # gövde metni (header hariç)
    if existing:
        body = "".join(lines[1:])
    else:
        body = "".join(lines)

    new_hash = compute_body_hash(body)
    today = datetime.date.today().isoformat()
    part = part_override or (existing['part'] if existing else '1/1')

    if existing:
        changed = (new_hash != existing['hash'])
        major = existing['major']
        minor = existing['minor']
        if changed:
            if bump_major:
                major += 1
                minor = 0
            else:
                minor += 1
        # tarih/hash güncelle
        header = format_header(prefix, suffix, major, minor, today, new_hash, part)
        new_text = header + body
        updated = changed or (existing['date'] != today) or part_override
    else:
        # ilk header
        header = format_header(prefix, suffix, 1, 0, today, new_hash, part)
        new_text = header + body
        updated = True

    if updated:
        write_file(path, new_text)
        if not quiet:
            print(f"[REV] {path}: güncellendi (hash={new_hash})")
    else:
        if not quiet:
            print(f"[REV] {path}: değişiklik yok (hash sabit)")
    # 650 satır uyarısı
    total_lines = new_text.count('\n') + 1
    if total_lines > 650 and not quiet:
        print(f"[UYARI] {path}: {total_lines} satır (>650). Bölmeyi düşünün (Parça i/N).")
    return 0

def should_skip(path):
    name = os.path.basename(path).lower()
    if name.startswith('.') or '/.git/' in path.replace('\\','/'):
        return True
    # binary kaba kontrol
    try:
        with open(path, 'rb') as f:
            chunk = f.read(2048)
        if b'\x00' in chunk: return True
    except: return True
    return False

def walk_and_process(root, patterns, **opts):
    ok=0
    for base in root:
        for dirpath, _, filenames in os.walk(base):
            for fn in filenames:
                path = os.path.join(dirpath, fn)
                if should_skip(path): continue
                if patterns and not any(path.endswith(p) for p in patterns):
                    continue
                try:
                    process_file(path, **opts)
                except Exception as e:
                    print(f"[HATA] {path}: {e}", file=sys.stderr); ok=1
    return ok

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('paths', nargs='*', default=['.'], help='Kök klasör(ler)')
    ap.add_argument('--ext', nargs='*', default=['.py','.html','.css','.js','.ts','.md','.yml','.yaml','.json','.ini','.cfg'])
    ap.add_argument('--bump-major', action='store_true')
    ap.add_argument('--part', help='i/N formatında parçayı zorla, ör: 2/3')
    ap.add_argument('--quiet', action='store_true')
    args = ap.parse_args()
    sys.exit(walk_and_process(args.paths, args.ext,
                              bump_major=args.bump_major,
                              part_override=args.part, quiet=args.quiet))
if __name__ == '__main__':
    main()
