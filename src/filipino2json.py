import csv
import json
import os
import re
from collections import defaultdict

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Filipino WordNet (Borra et al., 2010), filwordnet.csv
# Columns: wordid, lemma, synsetid, senseid, pos, lexdomainid, definition, lastmodifier, sumo
#
# synsetid = 1 digit for the part of speech (1 n, 2 v, 3 a/s, 4 r) + 8-digit Princeton WordNet offset.
# The paper says the translators used WordNet 3.0 synset numbers, so only PWN 3.0 offsets are accepted:
# an offset found in cili.tsv gets its ILI, all others (about 1,600 synsets that are PWN 2.0 offsets)
# get no ILI.

POS_FROM_PREFIX = {'1': 'n', '2': 'v', '3': 'a', '4': 'r'}


def clean_text(text):
    if not text:
        return text
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def split_lemmas(lemma):
    """'base/beys' -> ['base', 'beys'], 'aktib\\' -> ['aktib'], 'carbon_paper' -> ['carbon paper']"""
    lemma = lemma.replace('\\', '').replace('_', ' ').rstrip('?')
    return [clean_text(p) for p in lemma.split('/') if clean_text(p)]


def clean_sumo(sumo):
    """'Process[' -> 'Process', 'Female Human@' -> 'Female Human', 'None' -> ''"""
    sumo = re.sub(r'[\[\]@=+:]', '', sumo or '').strip()
    return '' if sumo == 'None' else sumo


def _load_ili_lookup(cili_path):
    """(offset, pos) -> ILI from cili.tsv (origin looks like pwn-3.0:00001740-a)"""
    pwn_2_ili = {}
    with open(cili_path, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            offset = row['origin'][8:16]
            pos = row['origin'][17:18]
            pos = 'a' if pos == 's' else pos
            pwn_2_ili[(offset, pos)] = row['ili_id']
    return pwn_2_ili


def convert_to_json(raw_dir='data/raw/filipino', csv_file='filwordnet.csv', cili_path='data/cili.tsv'):
    """
    Convert Filipino WordNet (CSV) into the standard GWA LMF-style dict
    used across all converters in this project.

    Returns
    -------
    dict with keys: 'meta', 'synsets', 'lexical_entries'
    """
    pwn_2_ili = _load_ili_lookup(cili_path)

    synsets = {}
    senses = []   # (synset_id, lemma)

    with open(f'{raw_dir}/{csv_file}', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            synset_id = row['synsetid'].strip()
            if not re.fullmatch(r'[1-4]\d{8}', synset_id):
                continue

            # the part of speech comes from the synset id (the pos column is wrong in 49 rows);
            # adjective satellites are marked 's' in the pos column
            pos = POS_FROM_PREFIX[synset_id[0]]
            if pos == 'a' and row['pos'].strip() == 's':
                pos = 's'

            if synset_id not in synsets:
                offset_pos = (synset_id[1:], POS_FROM_PREFIX[synset_id[0]])
                synsets[synset_id] = {
                    'id': synset_id,
                    'ili': pwn_2_ili.get(offset_pos, ''),
                    'pos': pos,
                    'definition': clean_text(row['definition']),
                    'examples': [],
                    'semfield': clean_sumo(row['sumo']),
                    'relations': []
                }
            elif pos == 's':
                synsets[synset_id]['pos'] = 's'

            for lemma in split_lemmas(row['lemma']):
                senses.append((synset_id, lemma))

    lemma_to_synsets = defaultdict(list)
    for synset_id, lemma in senses:
        key = (lemma, synsets[synset_id]['pos'])
        if synset_id not in lemma_to_synsets[key]:
            lemma_to_synsets[key].append(synset_id)

    lexical_entries = [
        {'id': i, 'lemma': lemma, 'pos': pos, 'senses': synset_ids}
        for i, ((lemma, pos), synset_ids) in enumerate(lemma_to_synsets.items())
    ]

    return {
        'meta': {
            'id': 'filwordnet-fil',
            'label': 'Filipino WordNet',
            'language': 'fil',
            'email': 'iga.masniak@ens.psl.eu',
            'license': '',
            'version': '1.0',
            'dc:creator': 'Allan Borra, Adam Pease, Rachel Edita Roxas, Shirley Dita',
            'dc:contributor': 'Iga Masniak',
            'dc:source': 'https://github.com/danjohnvelasco/Filipino-WordNet',
            'dc:description': 'Filipino WordNet converted to GWA LMF format by Iga Masniak'
        },
        'synsets': list(synsets.values()),
        'lexical_entries': lexical_entries
    }


if __name__ == '__main__':
    result = convert_to_json()
    with open('data/jsons/FilipinoWordNet_standard.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=4, ensure_ascii=False)

    print('Done: FilipinoWordNet_standard.json')
    print(f"Synsets: {len(result['synsets'])}")
    print(f"Lexical entries: {len(result['lexical_entries'])}")
    print(f"Synsets with ILI: {sum(1 for s in result['synsets'] if s['ili'])}")