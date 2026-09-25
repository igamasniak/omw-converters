
import argparse
import csv
import lzma
import os
import re
import sys

from lxml import etree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_XML_DIR = os.path.join(ROOT, "data", "xmls")
DEFAULT_CSV = os.path.join(ROOT, "data", "stats.csv")

CILI_RE = re.compile(r"^i\d+$")
FIELDS = ["file", "label", "language", "total", "cili", "pct", "no_ili"]


def open_xml(path):
    """Open an .xml or .xml.xz file in binary mode."""
    if path.endswith(".xz"):
        return lzma.open(path, "rb")
    return open(path, "rb")


def count_synsets(path):
    """Return a list of stats dicts, one per Lexicon found in the file."""
    lexicons = []
    current = None

    with open_xml(path) as f:
        for event, elem in etree.iterparse(
            f, events=("start", "end"), tag=("Lexicon", "Synset"),
            load_dtd=False, resolve_entities=False, huge_tree=True,
        ):
            if elem.tag == "Lexicon":
                if event == "start":
                    current = {
                        "file": os.path.basename(path),
                        "label": elem.get("label", ""),
                        "language": elem.get("language", ""),
                        "total": 0, "cili": 0, "no_ili": 0,
                    }
                    lexicons.append(current)
                else:
                    elem.clear()
                continue

            # Synset end event
            if event == "end" and current is not None:
                current["total"] += 1
                ili = (elem.get("ili") or "").strip()
                if CILI_RE.match(ili):
                    current["cili"] += 1
                else:
                    current["no_ili"] += 1
                elem.clear()

    for lex in lexicons:
        lex["pct"] = 100 * lex["cili"] / lex["total"] if lex["total"] else 0.0
    return lexicons


def collect_files(xml_dir):
    """List .xml files, plus .xml.xz files that have no uncompressed twin."""
    names = sorted(os.listdir(xml_dir))
    plain = {n for n in names if n.endswith(".xml")}
    files = []
    for n in names:
        if n.endswith(".xml"):
            files.append(n)
        elif n.endswith(".xml.xz") and n[:-3] not in plain:
            files.append(n)
    return [os.path.join(xml_dir, n) for n in files]


def print_table(rows):
    header = (f"{'Lexicon':<35} {'Lang':<6} {'Synsets':>9} {'CILI':>9} "
              f"{'%CILI':>7} {'No ILI':>9}")
    line = "-" * len(header)
    print(header)
    print(line)
    for r in rows:
        print(f"{r['label'][:35]:<35} {r['language']:<6} {r['total']:>9,} "
              f"{r['cili']:>9,} {r['pct']:>6.1f}% {r['no_ili']:>9,}")

    total = sum(r["total"] for r in rows)
    cili = sum(r["cili"] for r in rows)
    no_ili = sum(r["no_ili"] for r in rows)
    pct = 100 * cili / total if total else 0.0
    print(line)
    print(f"{'ALL (' + str(len(rows)) + ' lexicons)':<35} {'':<6} {total:>9,} "
          f"{cili:>9,} {pct:>6.1f}% {no_ili:>9,}")


def write_csv(rows, csv_path):
    os.makedirs(os.path.dirname(os.path.abspath(csv_path)), exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for r in rows:
            writer.writerow({**r, "pct": f"{r['pct']:.2f}"})


def main():
    parser = argparse.ArgumentParser(description="Synset / CILI statistics for WN-LMF files.")
    parser.add_argument("xml_dir", nargs="?", default=DEFAULT_XML_DIR,
                        help=f"directory with .xml / .xml.xz files (default: {DEFAULT_XML_DIR})")
    parser.add_argument("-o", "--output", default=DEFAULT_CSV,
                        help=f"CSV output path (default: {DEFAULT_CSV})")
    parser.add_argument("--sort", choices=["file", "total", "pct"], default="file",
                        help="sort order of the table (default: file)")
    args = parser.parse_args()

    if not os.path.isdir(args.xml_dir):
        sys.exit(f"Directory not found: {args.xml_dir}")

    rows = []
    for path in collect_files(args.xml_dir):
        try:
            rows.extend(count_synsets(path))
        except etree.XMLSyntaxError as e:
            print(f"SKIPPED {os.path.basename(path)}: {e}", file=sys.stderr)

    if not rows:
        sys.exit("No lexicons found.")

    if args.sort == "total":
        rows.sort(key=lambda r: r["total"], reverse=True)
    elif args.sort == "pct":
        rows.sort(key=lambda r: r["pct"], reverse=True)

    print_table(rows)
    write_csv(rows, args.output)
    print(f"\nSaved to {args.output}")


if __name__ == "__main__":
    main()