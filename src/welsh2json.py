import os
import json
from collections import defaultdict

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# WNCY ids are 9 digits: 1 digit for part of speech + 8 digit PWN 3.1 offset
POS_CODES = {'1': 'n', '2': 'v', '3': 'a', '4': 'r'}

REL_TYPES = {
    'hypernym': 'hypernym',
    'hyponym': 'hyponym',
    'instance hypernym': 'instance_hypernym',
    'instance hyponym': 'instance_hyponym',
    'part meronym': 'mero_part',
    'part holonym': 'holo_part',
    'member meronym': 'mero_member',
    'member holonym': 'holo_member',
    'substance meronym': 'mero_substance',
    'substance holonym': 'holo_substance',
    'similar': 'similar',
    'verb group': 'similar',
    'also': 'also',
    'attribute': 'attribute',
    'entail': 'entails',
    'cause': 'causes',
    'domain category': 'domain_topic',
    'domain member category': 'has_domain_topic',
    'domain region': 'domain_region',
    'domain member region': 'has_domain_region',
    'domain usage': 'exemplifies',
    'domain member usage': 'is_exemplified_by',
}


def _load_ili_lookup(ili_map_path):
    """Reads ili-map-pwn31.tab (lines like 'i46360<TAB>02086723-n')."""
    pwn31_2_ili = {}
    with open(ili_map_path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) == 2:
                pwn31_2_ili[parts[1]] = parts[0]
    return pwn31_2_ili


def _split_id(wncy_id, pwn31_2_ili):
    """'102086723' -> ('02086723-n', 'i46360')"""
    wncy_id = str(wncy_id)
    offset = wncy_id[1:]
    pos = POS_CODES[wncy_id[0]]

    # adjectives: WNCY does not separate head (a) and satellite (s) adjectives
    if pos == 'a' and f'{offset}-a' not in pwn31_2_ili and f'{offset}-s' in pwn31_2_ili:
        pos = 's'

    key = f'{offset}-{pos}'
    return key, pos, pwn31_2_ili.get(key, '')


def convert_to_json(raw_path='data/raw/welsh/wncy.json', ili_map_path='data/ili-map-pwn31.tab'):

    pwn31_2_ili = _load_ili_lookup(ili_map_path)

    with open(raw_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # map WNCY ids to our synset ids
    id_map = {}
    synsets = {}
    for wncy_id in data['synsets']:
        synset_id, pos, ili = _split_id(wncy_id, pwn31_2_ili)
        id_map[str(wncy_id)] = synset_id
        synsets[synset_id] = {
            'id': synset_id,
            'ili': ili,
            'pos': pos,
            'definition': '',
            'examples': [],
            'semfield': '',
            'relations': []
        }

    # relations (only between synsets that exist in WNCY)
    for source, rels in data['links']['semantic'].items():
        source_id = id_map.get(str(source))
        if source_id is None:
            continue
        seen = set()
        for rel_name, targets in rels.items():
            rel_type = REL_TYPES.get(rel_name)
            if rel_type is None:
                print(f'Unknown relation skipped: {rel_name}')
                continue
            for target in targets:
                target_id = id_map.get(str(target))
                if target_id is None or (rel_type, target_id) in seen:
                    continue
                seen.add((rel_type, target_id))
                synsets[source_id]['relations'].append({
                    'relType': rel_type,
                    'target': target_id
                })

    # building lexical entries (one entry per lemma + part of speech)
    lemma_to_data = defaultdict(lambda: {'synsets': [], 'forms': set()})
    for lemma, wncy_ids in data['words'].items():
        lemma = lemma.strip()
        if not lemma:
            continue
        for wncy_id in wncy_ids:
            synset_id = id_map.get(str(wncy_id))
            if synset_id is None:
                continue
            entry = lemma_to_data[(lemma, synsets[synset_id]['pos'])]
            if synset_id not in entry['synsets']:
                entry['synsets'].append(synset_id)

    return {
        'meta': {
            'id': 'welsh-cy',
            'label': 'WordNet Cymraeg',
            'language': 'cy',
            'email': 'iga.masniak@ens.psl.eu',
            'license': 'https://opensource.org/licenses/BSD-2-Clause',
            'version': '',
            'dc:creator': 'Steven Neale, Irena Spasic and Dawn Knight',
            'dc:contributor': 'Iga Masniak',
            'dc:source': 'https://github.com/CorCenCC/wncy',
            'dc:description': 'WordNet Cymraeg converted to GWA LMF format by Iga Masniak'
        },
        'synsets': list(synsets.values()),
        'lexical_entries': [
            {
                'id': i,
                'lemma': lemma,
                'pos': pos,
                'senses': d['synsets'],
                'forms': sorted(d['forms'])
            }
            for i, ((lemma, pos), d) in enumerate(lemma_to_data.items())
        ]
    }


if __name__ == '__main__':
    result = convert_to_json()
    with open('data/jsons/WelshWordNet_standard.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=4, ensure_ascii=False)

    print('Done: WelshWordNet_standard.json')
    print(f"Synsets: {len(result['synsets'])}")
    print(f"Lexical entries: {len(result['lexical_entries'])}")
