import os
import xml.etree.ElementTree as ET

from src.common import IliResolver, build_output, make_synset, save_output

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RAW_DIR = 'data/raw/russian'
FILE_POS = ['N', 'V', 'A']

POS_MAP = {'N': 'n', 'V': 'v', 'Adj': 'a'}

RELATION_MAP = {
    'hypernym': 'hypernym',
    'hyponym': 'hyponym',
    'instance hypernym': 'instance_hypernym',
    'instance hyponym': 'instance_hyponym',
    'part meronym': 'mero_part',
    'part holonym': 'holo_part',
    'antonym': 'antonym',
    'entailment': 'entails',
    'cause': 'causes',
    'domain': 'domain_topic',
    'related': 'also',
    'POS-synonymy': 'similar',
}

META = {
    'id': 'russian-ru',
    'label': 'RuWordNet',
    'language': 'ru',
    'email': 'iga.masniak@ens.psl.eu',
    'license': 'https://creativecommons.org/licenses/by-sa/4.0/',
    'version': '2.0',
    'dc:creator': 'Natalia Loukachevitch',
    'dc:contributor': 'Iga Masniak',
    'dc:description': 'Russian WordNet (RuWordNet) converted to GWA LMF format by Iga Masniak'
}


def read_all(raw_dir, name):
    return [el for p in FILE_POS for el in ET.parse(f'{raw_dir}/{name}.{p}.xml').getroot()]


def read_source(raw_dir):
    links = {match.find('rwn-synset').get('id'): match.find('wn-synset').get('id')
             for match in ET.parse(f'{raw_dir}/ili.xml').getroot()}
    return (read_all(raw_dir, 'synsets'), read_all(raw_dir, 'senses'),
            read_all(raw_dir, 'synset_relations'), links)


def convert_to_json(raw_dir=RAW_DIR, cili_path='data/cili.tsv'):
    ili = IliResolver(cili_path)
    raw_synsets, raw_senses, raw_relations, links = read_source(raw_dir)

    synsets = {}
    for s in raw_synsets:
        synset_id = s.get('id')
        pos, synset_ili = POS_MAP.get(s.get('part_of_speech'), 'u'), ''
        if synset_id in links:
            offset, pwn_pos = links[synset_id].split('-')
            synset_ili = ili.get(offset, pwn_pos, '30')
            pos = pwn_pos if pwn_pos == 's' else pos
        synsets[synset_id] = make_synset(synset_id, pos, synset_ili, s.get('definition', ''))

    for r in raw_relations:
        source, target = r.get('parent_id'), r.get('child_id')
        if r.get('name') in RELATION_MAP and source in synsets and target in synsets:
            synsets[source]['relations'].append({'target': target, 'relType': RELATION_MAP[r.get('name')]})

    senses = [(s.get('name', '').lower(), synsets[s.get('synset_id')]['pos'], s.get('synset_id'))
              for s in raw_senses if s.get('synset_id') in synsets]
    return build_output(META, synsets, senses)


if __name__ == '__main__':
    save_output(convert_to_json(), 'RussianWordNet')