import os
import re

from src.common import build_output, make_synset, save_output

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RAW_PATH = 'data/raw/latin_revised/lwn31.ttl'
ILI_MAP_PATH = 'data/ili-map-pwn31.tab'

RELATIONS = {
    'wn:hypernym': 'hypernym',
    'wn:hyponym': 'hyponym',
    'wn:instance_hypernym': 'instance_hypernym',
    'wn:instance_hyponym': 'instance_hyponym',
    'wn:part_meronym': 'mero_part',
    'wn:part_holonym': 'holo_part',
    'wn:member_meronym': 'mero_member',
    'wn:member_holonym': 'holo_member',
    'wn:substance_meronym': 'mero_substance',
    'wn:substance_holonym': 'holo_substance',
    'wn:similar': 'similar',
    'wn:also': 'also',
    'wn:attribute': 'attribute',
    'wn:entail': 'entails',
    'wn:cause': 'causes',
    'wn:verb_group': 'similar',
    'wn:domain_category': 'domain_topic',
    'wn:domain_member_category': 'has_domain_topic',
    'wn:domain_region': 'domain_region',
    'wn:domain_member_region': 'has_domain_region',
    'wn:domain_usage': 'exemplifies',
    'wn:domain_member_usage': 'is_exemplified_by',
}

META = {
    'id': 'latin-revised-la',
    'label': 'Latin WordNet (Revision)',
    'language': 'la',
    'email': 'iga.masniak@ens.psl.eu',
    'license': 'https://creativecommons.org/licenses/by-sa/4.0/',
    'version': '2.0',
    'dc:creator': 'Eleonora Litta, Greta Franzini, Giulia Pedonese, Marco Passarotti',
    'dc:contributor': 'Iga Masniak',
    'dc:description': 'Latin WordNet Revision converted to GWA LMF format by Iga Masniak'
}


def load_ili_map(path):
    with open(path, encoding='utf-8') as f:
        return {parts[1]: parts[0] for parts in (line.split() for line in f) if len(parts) == 2}


def get_ili(pwn31_to_ili, offset, pos):
    candidates = ['a', 's'] if pos in ('a', 's') else [pos]
    return next((pwn31_to_ili[f'{offset}-{p}'] for p in candidates if f'{offset}-{p}' in pwn31_to_ili), '')


def read_source(path):
    labels, senses, synsets = {}, set(), {}
    with open(path, encoding='utf-8') as f:
        blocks = f.read().split('\n\n')

    for block in blocks:
        block = block.strip()
        head = block.split(' ', 1)[0]
        if head.startswith('wordnetLexicalEntry:'):
            entry = head.split(':', 1)[1]
            label = re.search(r'rdfs:label "((?:[^"\\]|\\.)*)"', block)
            if label:
                labels[entry] = label.group(1)
            senses |= {(entry, s) for s in re.findall(r'wordnetSynset:(\d{8}-[nvasr])', block)}
        elif head.startswith('wordnetLexicalSense:'):
            entry = re.search(r'isSenseOf wordnetLexicalEntry:([^\s;.,]+)', block)
            synset = re.search(r'isLexicalizedSenseOf wordnetSynset:(\d{8}-[nvasr])', block)
            if entry and synset:
                senses.add((entry.group(1), synset.group(1)))
        elif head.startswith('wordnetSynset:'):
            synset = synsets.setdefault(head.split(':', 1)[1], {'definition': '', 'relations': []})
            definition = re.search(r'skos:definition "((?:[^"\\]|\\.)*)"', block)
            if definition:
                synset['definition'] = definition.group(1)
            for statement in block.split(';'):
                parts = statement.strip().split(None, 1)
                if len(parts) == 2 and parts[0] in RELATIONS:
                    synset['relations'] += [{'target': t, 'relType': RELATIONS[parts[0]]}
                                            for t in re.findall(r'wordnetSynset:(\d{8}-[nvasr])', parts[1])]
    return labels, senses, synsets


def convert_to_json(raw_path=RAW_PATH, ili_map_path=ILI_MAP_PATH):
    pwn31_to_ili = load_ili_map(ili_map_path)
    labels, sense_pairs, raw_synsets = read_source(raw_path)

    used = {synset_id for _, synset_id in sense_pairs if synset_id in raw_synsets}
    synsets = {}
    for synset_id in sorted(used):
        offset, pos = synset_id.split('-')
        synset_ili = get_ili(pwn31_to_ili, offset, pos)
        relations = [r for r in raw_synsets[synset_id]['relations'] if r['target'] in used]
        synsets[synset_id] = make_synset(synset_id, pos, synset_ili,
                                         raw_synsets[synset_id]['definition'], relations=relations)

    senses = [(labels[entry], synset_id.split('-')[1], synset_id)
              for entry, synset_id in sorted(sense_pairs) if entry in labels]
    return build_output(META, synsets, senses)


if __name__ == '__main__':
    save_output(convert_to_json(), 'LatinWordNet_revised')
