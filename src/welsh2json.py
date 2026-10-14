import json
import os

from src.common import build_output, make_synset, save_output

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RAW_PATH = 'data/raw/welsh/wncy.json'
ILI_MAP_PATH = 'data/ili-map-pwn31.tab'

POS_CODES = {'1': 'n', '2': 'v', '3': 'a', '4': 'r'}

RELATION_MAP = {
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

META = {
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
}


def load_ili_map(path):
    with open(path, encoding='utf-8') as f:
        return {parts[1]: parts[0] for parts in (line.split() for line in f) if len(parts) == 2}


def split_id(wncy_id, pwn31_to_ili):
    offset, pos = wncy_id[1:], POS_CODES[wncy_id[0]]
    if pos == 'a' and f'{offset}-a' not in pwn31_to_ili and f'{offset}-s' in pwn31_to_ili:
        pos = 's'
    return f'{offset}-{pos}', pos, pwn31_to_ili.get(f'{offset}-{pos}', '')


def read_source(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def convert_to_json(raw_path=RAW_PATH, ili_map_path=ILI_MAP_PATH):
    pwn31_to_ili = load_ili_map(ili_map_path)
    data = read_source(raw_path)

    id_map, synsets = {}, {}
    for wncy_id in data['synsets']:
        synset_id, pos, ili = split_id(str(wncy_id), pwn31_to_ili)
        id_map[str(wncy_id)] = synset_id
        synsets[synset_id] = make_synset(synset_id, pos, ili)

    for source, rels in data['links']['semantic'].items():
        if str(source) not in id_map:
            continue
        relations = synsets[id_map[str(source)]]['relations']
        for rel_name, targets in rels.items():
            for target in targets:
                if rel_name in RELATION_MAP and str(target) in id_map:
                    relation = {'target': id_map[str(target)], 'relType': RELATION_MAP[rel_name]}
                    if relation not in relations:
                        relations.append(relation)

    senses = [(lemma, synsets[id_map[str(w)]]['pos'], id_map[str(w)])
              for lemma, wncy_ids in data['words'].items() for w in wncy_ids if str(w) in id_map]
    return build_output(META, synsets, senses)


if __name__ == '__main__':
    save_output(convert_to_json(), 'WelshWordNet')