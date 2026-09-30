import csv
import json
import os
import re
from collections import defaultdict

from WordNetMapper import WordNetMapper

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# The YAML file has no Princeton WordNet offsets of its own, but its synset IDs are the same numbers
# as the hindi_id column of new_indo_wordnet.tsv (checked with check_bengali_ids.py: 6,900 of 6,901
# shared IDs have the same part of speech, 58% share a word with the Hindi/Sanskrit/Marathi synset).
# That file gives the PWN 2.1 offset (english_id) for each ID, so:
# ID -> english_id -> WordNetMapper 2.1 -> 3.0 -> cili.tsv -> ILI
# An ILI is only given when the part of speech also matches the TSV.

POS_MAP = {
    'NOUN': 'n',
    'VERB': 'v',
    'ADJECTIVE': 'a',
    'ADVERB': 'r',
}


def clean_text(text):
    if not text:
        return text
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    text = text.strip().strip('"').strip()
    return re.sub(r'\s+', ' ', text)


def split_examples(text):
    """'"first example"/"second example"' -> ['first example', 'second example']"""
    if not text:
        return []
    return [clean_text(p) for p in text.split('/') if clean_text(p)]


def split_lemmas(text):
    """'পবিত্র_স্থান, পুণ্য_ভূমি' -> ['পবিত্র স্থান', 'পুণ্য ভূমি']"""
    return [clean_text(p.replace('_', ' ')) for p in text.split(',') if clean_text(p)]


def _load_ili_lookup(cili_path):
    pwn_2_ili = {}
    with open(cili_path, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            pwn_2_ili[row['origin'][8:16]] = row['ili_id']
    return pwn_2_ili


def _load_id_to_ili(indo_tsv_path, cili_path):
    """synset id -> (ILI, part of speech in the TSV), using the english_id (PWN 2.1 offset) column"""
    my_mapper = WordNetMapper()
    pwn_2_ili = _load_ili_lookup(cili_path)
    id_2_ili = {}
    with open(indo_tsv_path, encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            try:
                english_id = f"{int(row['english_id']):08d}"
                pwn_offset, pos = my_mapper.map_offset_to_offset(english_id, "21", "30")
                tsv_pos = POS_MAP.get((row.get('hindi_category_x') or '').strip().upper(), '')
                id_2_ili[row['hindi_id']] = (pwn_2_ili[pwn_offset], tsv_pos)
            except Exception:
                continue
    return id_2_ili


def _read_records(yaml_path):

    records = []
    current = None
    with open(yaml_path, encoding='utf-8') as f:
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


def convert_to_json(raw_dir='data/raw/bengali',
                    yaml_file='synsets.yaml',
                    indo_tsv_path='data/new_indo_wordnet.tsv',
                    cili_path='data/cili.tsv'):

    id_2_ili = _load_id_to_ili(indo_tsv_path, cili_path)

    synsets = []
    senses = []   # (synset_id, lemma, pos)

    for record in _read_records(f'{raw_dir}/{yaml_file}'):
        synset_id = record.get('ID', '').strip()
        pos = POS_MAP.get(record.get('CAT', '').strip(), 'u')
        if not synset_id:
            continue

        ili, tsv_pos = id_2_ili.get(synset_id, ('', ''))
        if tsv_pos and tsv_pos != pos:
            ili = ''   # same ID but different part of speech: not the same concept

        synsets.append({
            'id': synset_id,
            'ili': ili,
            'pos': pos,
            'definition': clean_text(record.get('CONCEPT', '')),
            'examples': split_examples(record.get('EXAMPLE', '')),
            'semfield': '',
            'relations': []
        })

        for lemma in split_lemmas(record.get('SYNSET-BENGALI', '')):
            senses.append((synset_id, lemma, pos))

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
        },
        'synsets': synsets,
        'lexical_entries': lexical_entries
    }


if __name__ == '__main__':
    result = convert_to_json()
    with open('data/jsons/BengaliWordNet_standard.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=4, ensure_ascii=False)

    print('Done: BengaliWordNet_standard.json')
    print(f"Synsets: {len(result['synsets'])}")
    print(f"Lexical entries: {len(result['lexical_entries'])}")
    print(f"Synsets with ILI: {sum(1 for s in result['synsets'] if s['ili'])}")