import csv
import os
import json
import re
import unicodedata
from collections import defaultdict

from WordNetMapper import WordNetMapper

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# USGW synset IDs are Princeton WordNet 2.1 offsets (e.g. 00007626-n = "person"),
# so they are mapped 2.1 -> 3.0 with WordNetMapper and then looked up in cili.tsv.

NO_GLOSS = 'NO_GLOSS'


def clean_text(text):
    if not text:
        return text
    text = unicodedata.normalize('NFC', text)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    text = text.replace('’', "'").replace('‘', "'")   # curly apostrophes -> '
    text = text.replace('  s ', " 's ")                           # "an siud  s an seo" -> "an siud 's an seo"
    text = re.sub(r"^;(?=[A-Za-zÀ-ÿ])", "'", text)                # ";S e ..." -> "'S e ..."
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def split_lemma(lemma):
    """'aghaidh, gnùis' -> ['aghaidh', 'gnùis'], but keep real phrases with commas intact."""
    parts = [p.strip() for p in lemma.split(',')]
    if len(parts) > 1 and all(p and ' ' not in p for p in parts):
        return parts
    return [lemma]


def merge_glosses(glosses):
    """Deduplicate glosses coming from several rows and drop ones contained in a longer gloss."""
    unique = []
    for g in glosses:
        if g and g not in unique:
            unique.append(g)
    kept = [g for g in unique if not any(g != other and g in other for other in unique)]
    return '; '.join(kept)


def _load_ili_lookup(cili_path):
    pwn_2_ili = {}
    with open(cili_path, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            pwn_2_ili[row['origin'][8:16]] = row['ili_id']
    return pwn_2_ili


def _get_ili(my_mapper, pwn_2_ili, synset_id):
    offset = synset_id.split('-')[0]
    try:
        pwn_offset, mapped_pos = my_mapper.map_offset_to_offset(offset, "21", "30")
        return pwn_2_ili.get(pwn_offset, '')
    except Exception:
        return ''


def _read_rows(tab_path):
    """Rows look like: 00007626-n <TAB> gla:lemma <TAB> duine <TAB> EOMW"""
    with open(tab_path, 'r', encoding='utf-8-sig', newline='') as f:
        for line_no, line in enumerate(f.read().splitlines(), 1):
            if not line.strip():
                continue
            cols = line.split('\t')
            if len(cols) != 4:
                print(f'Skipping malformed line {line_no}: {line!r}')
                continue
            yield [c.strip() for c in cols]


def convert_to_json(raw_dir='data/raw/scottish_gaelic',
                    tab_file='USGW_v0.9.tab',
                    cili_path='data/cili.tsv'):
    """
    Convert the Unified Scottish Gaelic Wordnet (USGW) tab file into the standard
    GWA LMF-style dict used across all converters in this project.

    Returns
    -------
    dict with keys: 'meta', 'synsets', 'lexical_entries'
    """
    my_mapper = WordNetMapper()
    pwn_2_ili = _load_ili_lookup(cili_path)

    synset_order = []
    synset_pos = {}
    glosses = defaultdict(list)
    examples = defaultdict(list)
    senses = []   # (synset_id, lemma, pos)
    suspicious = []

    for synset_id, field, value, source in _read_rows(f'{raw_dir}/{tab_file}'):
        match = re.fullmatch(r'(\d{8})-([nvars])', synset_id)
        if not match:
            print(f'Skipping unknown synset id: {synset_id}')
            continue
        pos = match.group(2)

        if synset_id not in synset_pos:
            synset_pos[synset_id] = pos
            synset_order.append(synset_id)

        value = clean_text(value)
        if not value or value == NO_GLOSS:
            continue
        if '`' in value:
            suspicious.append((synset_id, field, value))

        if field == 'gla:lemma':
            for lemma in split_lemma(value):
                senses.append((synset_id, lemma, pos))
        elif field == 'gla:gloss':
            glosses[synset_id].append(value)
        elif field == 'gla:example':
            if value not in examples[synset_id]:
                examples[synset_id].append(value)
        else:
            print(f'Unknown field {field} for {synset_id}')

    synsets = []
    no_ili = []
    for synset_id in synset_order:
        ili = _get_ili(my_mapper, pwn_2_ili, synset_id)
        if not ili:
            no_ili.append(synset_id)
        synsets.append({
            'id': synset_id,
            'ili': ili,
            'pos': synset_pos[synset_id],
            'definition': merge_glosses(glosses[synset_id]),
            'examples': examples[synset_id],
            'semfield': '',
            'relations': []
        })

    lemma_to_synsets = defaultdict(list)
    for synset_id, lemma, pos in senses:
        key = (lemma, pos)
        if synset_id not in lemma_to_synsets[key]:
            lemma_to_synsets[key].append(synset_id)

    lexical_entries = [
        {'id': i, 'lemma': lemma, 'pos': pos, 'senses': synset_ids}
        for i, ((lemma, pos), synset_ids) in enumerate(lemma_to_synsets.items())
    ]

    return {
        'meta': {
            'id': 'usgw-gd',
            'label': 'Unified Scottish Gaelic Wordnet',
            'language': 'gd',
            'email': 'iga.masniak@ens.psl.eu',
            'license': 'CC BY-NC 3.0',
            'version': '0.9',
            'dc:creator': 'Gábor Bella, Fiona McNeill, Rody Gorman, Caoimhín Ó Donnaíle, Kirsty MacDonald, '
                          'Yamini Chandrashekar, Abed Alhakim Freihat, Fausto Giunchiglia',
            'dc:contributor': 'Iga Masniak',
            'dc:source': '',
            'dc:description': 'Unified Scottish Gaelic Wordnet converted to GWA LMF format by Iga Masniak'
        },
        'synsets': synsets,
        'lexical_entries': lexical_entries
    }


if __name__ == '__main__':
    result = convert_to_json()
    with open('data/jsons/ScottishGaelicWordNet_standard.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=4, ensure_ascii=False)

    print('Done: ScottishGaelicWordNet_standard.json')
    print(f"Synsets: {len(result['synsets'])}")
    print(f"Lexical entries: {len(result['lexical_entries'])}")
