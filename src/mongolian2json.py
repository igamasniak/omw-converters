import csv
import json
import os
import re
from collections import defaultdict

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def clean_text(text):
    if not text:
        return text
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def split_gloss(text):

    match = re.search(r'\s*;\s*[“"]', text)
    if not match:
        return clean_text(text), []
    definition = text[:match.start()]
    examples = re.findall(r'[“"]([^”"]+)[”"]', text[match.start():])
    return clean_text(definition), [clean_text(e) for e in examples if clean_text(e)]


def _load_ili_lookup(cili_path):
    """(offset, n/v/a/r) -> (ILI, pos as in PWN 3.0, i.e. with 's' for satellites)"""
    pwn_2_ili = {}
    with open(cili_path, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            offset = row['origin'][8:16]
            pos = row['origin'][17:18]
            pwn_2_ili[(offset, 'a' if pos == 's' else pos)] = (row['ili_id'], pos)
    return pwn_2_ili


def convert_to_json(raw_dir='data/raw/mongolian', tab_file='wn-data-mon.tsv', cili_path='data/cili.tsv'):
    """
    Convert the Mongolian Wordnet (OMW tab file) into the standard GWA LMF-style dict
    used across all converters in this project.

    Returns
    -------
    dict with keys: 'meta', 'synsets', 'lexical_entries'
    """
    pwn_2_ili = _load_ili_lookup(cili_path)

    order = []
    definitions = {}
    examples = defaultdict(list)
    lemmas = defaultdict(list)

    with open(f'{raw_dir}/{tab_file}', encoding='utf-8') as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            cols = line.rstrip('\n').split('\t')
            if len(cols) != 3 or not re.fullmatch(r'\d{8}-[nvasr]', cols[0]):
                continue
            synset_id, field, value = cols
            value = clean_text(value)
            if not value:
                continue
            if synset_id not in lemmas and synset_id not in definitions and synset_id not in examples:
                order.append(synset_id)

            if field == 'mon:lemma':
                if value not in lemmas[synset_id]:
                    lemmas[synset_id].append(value)
            elif field.startswith('mon:def'):
                definition, gloss_examples = split_gloss(value)
                definitions[synset_id] = definition
                examples[synset_id].extend(gloss_examples)
            elif field.startswith('mon:exe'):
                examples[synset_id].append(value)

    synsets = []
    synset_pos = {}
    for synset_id in order:
        offset, pos = synset_id.split('-')
        pos = 'a' if pos == 's' else pos
        ili, pwn_pos = pwn_2_ili.get((offset, pos), ('', pos))
        synset_pos[synset_id] = pwn_pos
        synsets.append({
            'id': synset_id,
            'ili': ili,
            'pos': pwn_pos,
            'definition': definitions.get(synset_id, ''),
            'examples': list(dict.fromkeys(examples[synset_id])),
            'semfield': '',
            'relations': []
        })

    lemma_to_synsets = defaultdict(list)
    for synset_id in order:
        for lemma in lemmas[synset_id]:
            key = (lemma, synset_pos[synset_id])
            if synset_id not in lemma_to_synsets[key]:
                lemma_to_synsets[key].append(synset_id)

    lexical_entries = [
        {'id': i, 'lemma': lemma, 'pos': pos, 'senses': synset_ids}
        for i, ((lemma, pos), synset_ids) in enumerate(lemma_to_synsets.items())
    ]

    return {
        'meta': {
            'id': 'monwn-mn',
            'label': 'Mongolian Wordnet',
            'language': 'mn',
            'email': 'iga.masniak@ens.psl.eu',
            'license': 'https://creativecommons.org/licenses/by/4.0/',
            'version': '',
            'dc:creator': 'Khuyagbaatar Batsuren, Amarsanaa Ganbold, Altangerel Chagnaa, Fausto Giunchiglia',
            'dc:contributor': 'Iga Masniak',
            'dc:source': 'https://github.com/kbatsuren/monwn',
            'dc:description': 'Mongolian Wordnet (MonWN) converted to GWA LMF format by Iga Masniak'
        },
        'synsets': synsets,
        'lexical_entries': lexical_entries
    }


if __name__ == '__main__':
    result = convert_to_json()
    with open('data/jsons/MongolianWordNet_standard.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=4, ensure_ascii=False)

    print('Done: MongolianWordNet_standard.json')
    print(f"Synsets: {len(result['synsets'])}")
    print(f"Lexical entries: {len(result['lexical_entries'])}")
    print(f"Synsets with ILI: {sum(1 for s in result['synsets'] if s['ili'])}")
