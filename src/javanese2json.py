import csv
import os
import json
from collections import defaultdict

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def _load_ili_lookup(cili_path):
    pwn_2_ili = {}
    with open(cili_path, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            pwn_2_ili[row['origin'][8:16]] = row['ili_id']
    return pwn_2_ili


def convert_to_json(raw_csv_path='data/raw/javanese/wn-kaw.csv', cili_path='data/cili.tsv'):
    """
    Convert Old Javanese WordNet raw CSV into the standard GWA LMF-style
    dict used across all converters in this project.

    Parameters
    ----------
    raw_csv_path : str
        Path to the wn-kaw.csv file
    cili_path : str
        Path to the cili.tsv ILI lookup file

    Returns
    -------
    dict with keys: 'meta', 'synsets', 'lexical_entries'
    """
    pwn_2_ili = _load_ili_lookup(cili_path)

    synsets = {}
    senses = []  # (offset, lemma, [alternate_forms])

    with open(raw_csv_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            parts = line.split('\t')
            if len(parts) < 3:
                continue

            offset_pos = parts[0]
            lemma = parts[2].strip()

            offset, pos = offset_pos.rsplit('-', 1)

            # ILI lookup (PWN 3.0)
            ili = pwn_2_ili.get(offset, '')

            # storing synset
            if offset not in synsets:
                synsets[offset] = {
                    'id': offset,
                    'ili': ili,
                    'pos': pos,
                    'definition': '',
                    'examples': [],
                    'semfield': '',
                    'relations': []
                }

            # alternate forms (4th column)
            alt_forms = []
            if len(parts) >= 4 and parts[3].strip():
                for alt in parts[3].strip().split(','):
                    alt = alt.strip()
                    if alt:
                        alt_forms.append(alt)

            # Store sense with alternate forms
            if lemma:
                senses.append((offset, lemma, alt_forms))

    # building lexical entries
    lemma_to_data = defaultdict(lambda: {'synsets': [], 'forms': set()})
    for offset, lemma, alt_forms in senses:
        if offset not in lemma_to_data[lemma]['synsets']:
            lemma_to_data[lemma]['synsets'].append(offset)
        for alt in alt_forms:
            lemma_to_data[lemma]['forms'].add(alt)

    return {
        'meta': {
            'id': 'oldjavanese-kaw',
            'label': 'Old Javanese WordNet',
            'language': 'kaw',
            'email': 'iga.masniak@ens.psl.eu',
            'license': 'https://creativecommons.org/licenses/by/4.0/',
            'version': '1.0',
            'dc:creator': 'David Moeljadi and Zakariya Pamuji Aminullah',
            'dc:contributor': 'Iga Masniak',
            'dc:description': 'Old Javanese WordNet converted to GWA LMF format by Iga Masniak'
        },
        'synsets': list(synsets.values()),
        'lexical_entries': [
            {
                'id': i,
                'lemma': l,
                'senses': d['synsets'],
                'forms': sorted(d['forms'])
            }
            for i, (l, d) in enumerate(lemma_to_data.items())
        ]
    }


if __name__ == '__main__':
    result = convert_to_json()
    with open('data/jsons/OldJavaneseWordNet_standard.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=4, ensure_ascii=False)

    print('Done: OldJavaneseWordNet_standard.json')
    print(f"Synsets: {len(result['synsets'])}")
    print(f"Lexical entries: {len(result['lexical_entries'])}")