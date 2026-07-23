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


def convert_to_json(raw_tsv_path='data/raw/myanmar/mow-0.1.3-mya_20171005165336.tsv',
                     cili_path='data/cili.tsv'):
    """
    Convert Myanmar Open WordNet raw TSV into the standard GWA LMF-style
    dict used across all converters in this project.

    Parameters
    ----------
    raw_tsv_path : str
        Path to the Myanmar Open WordNet .tsv file
    cili_path : str
        Path to the cili.tsv ILI lookup file

    Returns
    -------
    dict with keys: 'meta', 'synsets', 'lexical_entries'
    """
    pwn_2_ili = _load_ili_lookup(cili_path)

    synsets_by_lang = defaultdict(list)
    senses_by_lang = defaultdict(list)
    seen_synsets = defaultdict(set)

    with open(raw_tsv_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('#'):
                continue
            parts = line.strip().split('\t')
            if len(parts) < 3:
                continue

            offset_pos = parts[0]       # e.g. 00001740-v
            lemma = parts[2].strip()    # e.g. ရှူ

            if not lemma:
                continue

            offset, pos = offset_pos.rsplit('-', 1)  # split into 00001740 and v

            # ILI lookup directly from cili.tsv (already PWN 3.0)
            ili = pwn_2_ili.get(offset, '')

            if offset_pos not in seen_synsets['Myanmar']:
                seen_synsets['Myanmar'].add(offset_pos)

                synsets_by_lang['Myanmar'].append({
                    'id': offset_pos,
                    'ili': ili,
                    'pos': pos,
                    'definition': '',
                    'examples': [],
                    'semfield': '',
                    'relations': []
                })

            senses_by_lang['Myanmar'].append((offset_pos, lemma))

    lang = 'Myanmar'
    lemma_to_synsets = defaultdict(list)

    for offset_pos, lemma in senses_by_lang[lang]:
        if offset_pos not in lemma_to_synsets[lemma]:
            lemma_to_synsets[lemma].append(offset_pos)

    return {
        'meta': {
            'id': 'myanmar-mya',
            'label': 'Myanmar Open WordNet',
            'language': 'mya',
            'email': 'iga.masniak@ens.psl.eu',
            'license': 'https://creativecommons.org/licenses/by/4.0/',
            'version': '0.1.3',
            'dc:creator': 'Wenjie Wang and Francis Bond',
            'dc:contributor': 'Iga Masniak',
            'dc:description': 'Myanmar Open WordNet converted to GWA LMF format by Iga Masniak'
        },
        'synsets': synsets_by_lang[lang],
        'lexical_entries': [
            {'id': i, 'lemma': l, 'senses': s} for i, (l, s) in enumerate(lemma_to_synsets.items())
        ]
    }


if __name__ == '__main__':
    result = convert_to_json()
    with open('data/jsons/MyanmarWordNet_standard.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=4, ensure_ascii=False)

    print('Done: MyanmarWordNet_standard.json')
    print(f"Synsets: {len(result['synsets'])}")
    print(f"Lexical entries: {len(result['lexical_entries'])}")