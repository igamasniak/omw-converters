import csv
import os
import json
import re
from collections import defaultdict

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POS_MAP = {
    'n': 'n',
    'v': 'v',
    'a': 'a',
    's': 's',
    'r': 'r'
}


def _load_ili_lookup(cili_path):
    pwn_2_ili = {}
    with open(cili_path, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            pwn_2_ili[row['origin'][8:16]] = row['ili_id']
    return pwn_2_ili


def convert_to_json(raw_csv_path='data/raw/latin_revised/LiLa_LatinWordnet.csv',
                     cili_path='data/cili.tsv'):
    """
    Convert the LiLa Latin WordNet CSV into the standard GWA LMF-style
    dict used across all converters in this project.

    Parameters
    ----------
    raw_csv_path : str
        Path to the LiLa_LatinWordnet.csv file
    cili_path : str
        Path to the cili.tsv ILI lookup file

    Returns
    -------
    dict with keys: 'meta', 'synsets', 'lexical_entries'
    """
    pwn_2_ili = _load_ili_lookup(cili_path)

    synsets = {}
    senses = []

    with open(raw_csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            lemma = row['lemma'].strip()
            definition = row['definition'].strip() if row['definition'] else ''
            synset_uri = row['id_synset'].strip()

            # Extract synset ID from URI: http://wordnet-rdf.princeton.edu/wn30/06831177-n
            m = re.search(r'wn30/(\d{8}-[a-z])', synset_uri)
            if not m or not lemma:
                continue

            synset_id = m.group(1)  # e.g. "06831177-n"
            offset = synset_id.split('-')[0]  # e.g. "06831177"
            pos = synset_id.split('-')[1]  # e.g. "n"

            # ILI lookup (direct, already PWN 3.0)
            ili = pwn_2_ili.get(offset, '')

            # Store synset (only first occurrence keeps definition)
            if synset_id not in synsets:
                synsets[synset_id] = {
                    'id': synset_id,
                    'ili': ili,
                    'pos': POS_MAP.get(pos, 'u'),
                    'definition': definition,
                    'examples': [],
                    'semfield': '',
                    'relations': []
                }

            # Store sense
            senses.append((synset_id, lemma))

    # --- Build lexical entries ---
    lemma_to_synsets = defaultdict(list)
    for synset_id, lemma in senses:
        if synset_id not in lemma_to_synsets[lemma]:
            lemma_to_synsets[lemma].append(synset_id)

    lexical_entries = []
    for i, (lemma, sense_list) in enumerate(lemma_to_synsets.items()):
        pos = POS_MAP.get(sense_list[0].split('-')[1], 'n') if sense_list else 'n'
        lexical_entries.append({
            'id': i,
            'lemma': lemma,
            'pos': pos,
            'senses': sense_list
        })

    return {
        'meta': {
            'id': 'latin-revised-csv-la',
            'label': 'Latin WordNet (LiLa CSV)',
            'language': 'la',
            'email': 'iga.masniak@ens.psl.eu',
            'license': 'https://creativecommons.org/licenses/by-nc-sa/4.0/',
            'version': '3.0',
            'dc:creator': 'Eleonora Litta, Greta Franzini, Giulia Pedonese, Marco Passarotti',
            'dc:contributor': 'Iga Masniak',
            'dc:description': 'LiLa Latin WordNet CSV (mapped to PWN 3.0) converted to GWA LMF format by Iga Masniak'
        },
        'synsets': list(synsets.values()),
        'lexical_entries': lexical_entries
    }


if __name__ == '__main__':
    result = convert_to_json()
    with open('data/jsons/LatinWordNet_revised_csv_standard.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=4, ensure_ascii=False)

    print('Done: LatinWordNet_revised_csv_standard.json')
    print(f"Synsets: {len(result['synsets'])}")
    print(f"Lexical entries: {len(result['lexical_entries'])}")
    print(f"With ILI: {sum(1 for s in result['synsets'] if s['ili'])}")