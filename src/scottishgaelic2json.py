import os
import re
import unicodedata
from collections import defaultdict

from src.common import IliResolver, build_output, make_synset, save_output

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RAW_PATH = 'data/raw/scottish_gaelic/USGW_v0.9.tab'

NO_GLOSS = 'NO_GLOSS'

META = {
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
}


def clean_gaelic(text):
    text = unicodedata.normalize('NFC', text or '')
    text = text.replace('’', "'").replace('‘', "'").replace('  s ', " 's ")
    return re.sub(r"^;(?=[A-Za-zÀ-ÿ])", "'", text).strip()


def split_lemma(lemma):
    parts = [p.strip() for p in lemma.split(',')]
    if len(parts) > 1 and all(p and ' ' not in p for p in parts):
        return parts
    return [lemma]


def merge_glosses(glosses):
    unique = list(dict.fromkeys(g for g in glosses if g))
    return '; '.join(g for g in unique if not any(g != other and g in other for other in unique))


def read_source(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        rows = [line.split('\t') for line in f.read().splitlines() if line.strip()]
    return [[c.strip() for c in row] for row in rows if len(row) == 4]


def convert_to_json(raw_path=RAW_PATH, cili_path='data/cili.tsv'):
    ili = IliResolver(cili_path)
    synset_pos, glosses, examples, senses = {}, defaultdict(list), defaultdict(list), []

    for synset_id, field, value, _ in read_source(raw_path):
        match = re.fullmatch(r'(\d{8})-([nvars])', synset_id)
        if not match:
            continue
        pos = synset_pos.setdefault(synset_id, match.group(2))
        value = clean_gaelic(value)
        if not value or value == NO_GLOSS:
            continue
        if field == 'gla:lemma':
            senses += [(lemma, pos, synset_id) for lemma in split_lemma(value)]
        elif field == 'gla:gloss':
            glosses[synset_id].append(value)
        elif field == 'gla:example':
            examples[synset_id].append(value)

    synsets = {
        synset_id: make_synset(synset_id, pos, ili.get(synset_id[:8], pos, '21'),
                               merge_glosses(glosses[synset_id]), examples[synset_id])
        for synset_id, pos in synset_pos.items()
    }
    return build_output(META, synsets, senses)


if __name__ == '__main__':
    save_output(convert_to_json(), 'ScottishGaelicWordNet')