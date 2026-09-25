#!/usr/bin/env python3
"""Pipeline for converting multilingual wordnets to WN-LMF 1.4 XML."""

import json
import lzma
import os
import sys
import xml.etree.ElementTree as ET
from lxml import etree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
JSON_DIR = os.path.join(ROOT, "data", "jsons")
XML_DIR = os.path.join(ROOT, "data", "xmls")
DTD_PATH = os.path.join(ROOT, "WN-LMF-1.4.dtd")

os.makedirs(JSON_DIR, exist_ok=True)
os.makedirs(XML_DIR, exist_ok=True)

from src.ancientgreek2json import convert_to_json as convert_ancientgreek
from src.welsh2json import convert_to_json as convert_welsh
from src.greek2json import convert_to_json as convert_greek
from src.finnish2json import convert_to_json as convert_finnish
from src.javanese2json import convert_to_json as convert_javanese
from src.latin2json import convert_to_json as convert_latin
from src.latinrevision2json import convert_to_json as convert_latin_revised
from src.latinrevisioncsv2json import convert_to_json as convert_latin_csv
from src.norwegian2json import convert_to_json as convert_norwegian
from src.romanian2json import convert_to_json as convert_romanian
from src.russian2json import convert_to_json as convert_russian
from src.sanskrit2json import convert_to_json as convert_sanskrit
from src.hungarian2json import convert_to_json as convert_hungarian
from src.indowordnet2json import convert_to_json as convert_indo

CONVERTERS = [
    ("Ancient Greek", convert_ancientgreek),
    ("Welsh", convert_welsh),
    ("Greek", convert_greek),
    ("Finnish", convert_finnish),
    ("Old Javanese", convert_javanese),
    ("Latin", convert_latin),
    ("Latin Revised (TTL)", convert_latin_revised),
    ("Latin Revised (CSV)", convert_latin_csv),
    ("Norwegian Bokmål", convert_norwegian),
    ("Romanian", convert_romanian),
    ("Russian", convert_russian),
    ("Hungarian", convert_hungarian),
    ("Sanskrit", convert_sanskrit),
    ("IndoWordNet Assamese", lambda: convert_indo("assamese")),
    ("IndoWordNet Bodo", lambda: convert_indo("bodo")),
    ("IndoWordNet English", lambda: convert_indo("english")),
    ("IndoWordNet Gujarati", lambda: convert_indo("gujarati")),
    ("IndoWordNet Hindi", lambda: convert_indo("hindi")),
    ("IndoWordNet Kannada", lambda: convert_indo("kannada")),
    ("IndoWordNet Kashmiri", lambda: convert_indo("kashmiri")),
    ("IndoWordNet Konkani", lambda: convert_indo("konkani")),
    ("IndoWordNet Malayalam", lambda: convert_indo("malayalam")),
    ("IndoWordNet Manipuri", lambda: convert_indo("manipuri")),
    ("IndoWordNet Marathi", lambda: convert_indo("marathi")),
    ("IndoWordNet Nepali", lambda: convert_indo("nepali")),
    ("IndoWordNet Odia", lambda: convert_indo("oriya")),
    ("IndoWordNet Punjabi", lambda: convert_indo("punjabi")),
    ("IndoWordNet Sanskrit", lambda: convert_indo("sanskrit")),
    ("IndoWordNet Tamil", lambda: convert_indo("tamil")),
    ("IndoWordNet Telugu", lambda: convert_indo("telugu")),
    ("IndoWordNet Urdu", lambda: convert_indo("urdu")),
]

REQUIRED_ATTRS = ["id", "label", "language", "email", "license", "version"]

DC_ATTRS = [
    "dc:creator", "dc:contributor", "dc:description", "dc:source",
    "dc:subject", "dc:publisher", "dc:rights", "dc:date",
]


def step_convert_to_json():
    print("\nStep 1: Raw data → standard JSON")
    print("-" * 40)
    for name, func in CONVERTERS:
        print(f"  {name}... ", end="", flush=True)
        try:
            func()
            print("ok")
        except Exception as e:
            print(f"FAILED ({e})")

def json_to_lmf(json_path, xml_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    meta = data["meta"]
    prefix = meta["id"]
    synset_pos = {s["id"]: s["pos"] for s in data["synsets"]}

    resource = ET.Element("LexicalResource")
    resource.set("xmlns:dc", "https://globalwordnet.github.io/schemas/dc/")

    lexicon = ET.SubElement(resource, "Lexicon")
    for attr in REQUIRED_ATTRS:
        lexicon.set(attr, meta[attr])
    for attr in DC_ATTRS:
        if attr in meta:
            lexicon.set(attr, meta[attr])

    for entry in data["lexical_entries"]:
        entry_id = f"{prefix}-lex{entry['id']}"
        le = ET.SubElement(lexicon, "LexicalEntry")
        le.set("id", entry_id)

        lemma = ET.SubElement(le, "Lemma")
        lemma.set("writtenForm", entry["lemma"].strip('"'))
        pos = entry.get("pos") or synset_pos.get(entry["senses"][0], "n")
        lemma.set("partOfSpeech", pos)

        for sid in entry["senses"]:
            sense = ET.SubElement(le, "Sense")
            sense.set("id", f"{prefix}-{sid}-{entry_id}")
            sense.set("synset", f"{prefix}-{sid}")

    for s in data["synsets"]:
        synset = ET.SubElement(lexicon, "Synset")
        synset.set("id", f"{prefix}-{s['id']}")
        synset.set("ili", s["ili"] if s["ili"] else "")
        synset.set("partOfSpeech", s["pos"])

        if s.get("semfield"):
            synset.set("dc:subject", s["semfield"])
        if s.get("definition"):
            ET.SubElement(synset, "Definition").text = s["definition"].strip('"')
        for rel in s.get("relations", []):
            r = ET.SubElement(synset, "SynsetRelation")
            r.set("target", f"{prefix}-{rel['target']}")
            r.set("relType", rel["relType"])
        for ex in s.get("examples", []):
            ET.SubElement(synset, "Example").text = ex

    ET.indent(resource, space="  ")
    xml_str = ET.tostring(resource, encoding="unicode", xml_declaration=True)
    xml_str = xml_str.replace(
        "<?xml version='1.0' encoding='us-ascii'?>",
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE LexicalResource SYSTEM "WN-LMF-1_4.dtd">',
    )

    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(xml_str)

def step_convert_to_xml():
    print("\nStep 2: Standard JSON → WN-LMF XML")
    print("-" * 40)
    for fname in sorted(os.listdir(JSON_DIR)):
        if not fname.endswith(".json"):
            continue
        json_path = os.path.join(JSON_DIR, fname)
        xml_name = fname.replace("_standard.json", ".xml").replace(".json", ".xml")
        xml_path = os.path.join(XML_DIR, xml_name)

        print(f"  {fname} → {xml_name}... ", end="", flush=True)
        try:
            json_to_lmf(json_path, xml_path)
            print("ok")
        except Exception as e:
            print(f"FAILED ({e})")

def validate_lmf(xml_path):
    with open(xml_path, "rb") as f:
        tree = etree.parse(f)
    with open(DTD_PATH, "rb") as f:
        dtd = etree.DTD(f)

    if dtd.validate(tree):
        return []
    return [f"line {err.line}: {err.message}" for err in dtd.error_log]


def step_validate():
    print("\nStep 3: Validate XML")
    print("-" * 40)

    if not os.path.exists(DTD_PATH):
        print(f"  ERROR: DTD not found at {DTD_PATH}")
        return False

    n_valid, n_invalid = 0, 0

    for fname in sorted(os.listdir(XML_DIR)):
        if not fname.endswith(".xml"):
            continue
        xml_path = os.path.join(XML_DIR, fname)
        errors = validate_lmf(xml_path)

        if not errors:
            print(f"  valid    {fname}")
            n_valid += 1
        else:
            print(f"  INVALID  {fname}")
            for err in errors:
                print(f"           {err}")
            n_invalid += 1

    print(f"\n  {n_valid} valid, {n_invalid} invalid")
    return n_invalid == 0


def step_compress():
    print("\nStep 4: Compress (XZ)")
    print("-" * 40)

    for fname in sorted(os.listdir(XML_DIR)):
        if not fname.endswith(".xml"):
            continue
        xml_path = os.path.join(XML_DIR, fname)
        xz_path = xml_path + ".xz"

        if os.path.exists(xz_path) and os.path.getmtime(xz_path) >= os.path.getmtime(xml_path):
            print(f"  {fname}.xz  up to date")
            continue

        with open(xml_path, "rb") as f_in:
            with lzma.open(xz_path, "wb", preset=6) as f_out:
                f_out.write(f_in.read())

        xml_size = os.path.getsize(xml_path)
        xz_size = os.path.getsize(xz_path)
        ratio = 100 * xz_size / xml_size if xml_size else 0
        print(f"  {fname}.xz  {xml_size:,} → {xz_size:,} bytes ({ratio:.0f}%)")


def main():
    step_convert_to_json()
    step_convert_to_xml()
    all_valid = step_validate()
    if not all_valid:
        print("\nValidation errors found. Fix before compressing.")
        sys.exit(1)
    step_compress()
    print("\nDone.")


if __name__ == "__main__":
    main()
