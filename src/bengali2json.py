import csv
import os
import re

from src.common import IliResolver, build_output, make_synset, save_output

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RAW_PATH = 'data/raw/bengali/synsets.yaml'
INDO_TSV_PATH = 'data/new_indo_wordnet.tsv'

POS_MAP = {
    'NOUN': 'n',
    'VERB': 'v',
    'ADJECTIVE': 'a',
    'ADVERB': 'r',
}

META = {
    'id': 'bangla-wordnet-bn',
    'label': 'Bangla WordNet',
    'language': 'bn',
    'email': 'iga.masniak@ens.psl.eu',
    'license': 'https://www.gnu.org/licenses/gpl-3.0.html',
    'version': '0.1',
    'dc:creator': 'Soumen Ganguly',
    'dc:contributor': 'Iga Masniak',
    'dc:source': 'https://github.com/soumenganguly/Bangla-Wordnet',
    'dc:description': 'Bangla WordNet converted to GWA LMF format by Iga Masniak'
}


def unquote(text):
    return (text or '').strip().strip('"').strip()


def split_examples(text):
    return [unquote(p) for p in (text or '').split('/') if unquote(p)]


def split_lemmas(text):
    return [unquote(p.replace('_', ' ')) for p in (text or '').split(',') if unquote(p)]


def load_english_ids(path):
    english_ids = {}
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            english_ids[row['hindi_id']] = (
                (row.get('english_id') or '').strip(),
                POS_MAP.get((row.get('hindi_category_x') or '').strip().upper(), '')
            )
    return english_ids


def read_source(path):
    records, current = [], None
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if line.strip() == '-':
                current = {}
                records.append(current)
                continue
            match = re.match(r'^\s*([A-Z-]+):\s?(.*)$', line)
            if match and current is not None:
                current[match.group(1)] = match.group(2)
    return records


def convert_to_json(raw_path=RAW_PATH, cili_path='data/cili.tsv', indo_tsv_path=INDO_TSV_PATH):
    ili = IliResolver(cili_path)
    english_ids = load_english_ids(indo_tsv_path)
    synsets, senses = {}, []

    for record in read_source(raw_path):
        synset_id = record.get('ID', '').strip()
        if not synset_id:
            continue
        pos = POS_MAP.get(record.get('CAT', '').strip(), 'u')

        english_id, tsv_pos = english_ids.get(synset_id, ('', ''))
        synset_ili = ili.get(english_id, pos, '21') if english_id and tsv_pos == pos else ''

        synsets[synset_id] = make_synset(synset_id, pos, synset_ili,
                                         unquote(record.get('CONCEPT')), split_examples(record.get('EXAMPLE')))
        senses += [(lemma, pos, synset_id) for lemma in split_lemmas(record.get('SYNSET-BENGALI'))]

    return build_output(META, synsets, senses)


if __name__ == '__main__':
    save_output(convert_to_json(), 'BengaliWordNet')