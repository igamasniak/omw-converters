import csv
import os
import json
import xml.etree.ElementTree as ET
from collections import defaultdict

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POS_MAP = {
    'N': 'n',
    'V': 'v',
    'Adj': 'a'
}

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


def _load_ili_lookup(cili_path):
    pwn_2_ili = {}
    with open(cili_path, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            pwn_2_ili[row['origin'][8:16]] = row['ili_id']
    return pwn_2_ili


def _load_rwn_to_ili(ili_xml_path, pwn_2_ili):
    ili_tree = ET.parse(ili_xml_path)
    ili_root = ili_tree.getroot()

    rwn_to_ili = {}
    for match in ili_root.findall('match'):
        rwn = match.find('rwn-synset')
        wn = match.find('wn-synset')
        if rwn is not None and wn is not None:
            rwn_id = rwn.get('id')
            wn_id = wn.get('id')
            # wn_id format: 11493827-n
            pwn_offset = wn_id.split('-')[0]
            ili = pwn_2_ili.get(pwn_offset, '')
            if ili:
                rwn_to_ili[rwn_id] = ili
    return rwn_to_ili


def convert_to_json(raw_dir='data/raw/russian', cili_path='data/cili.tsv'):
    """
    Convert Russian WordNet (RuWordNet) raw XML files into the standard
    GWA LMF-style dict used across all converters in this project.

    Parameters
    ----------
    raw_dir : str
        Directory containing ili.xml, synsets.*.xml, senses.*.xml,
        synset_relations.*.xml
    cili_path : str
        Path to the cili.tsv ILI lookup file

    Returns
    -------
    dict with keys: 'meta', 'synsets', 'lexical_entries'
    """
    pwn_2_ili = _load_ili_lookup(cili_path)
    rwn_to_ili = _load_rwn_to_ili(f'{raw_dir}/ili.xml', pwn_2_ili)

    synsets = {}
    synset_senses = defaultdict(list)

    for suffix in ['N', 'V', 'A']:
        tree = ET.parse(f'{raw_dir}/synsets.{suffix}.xml')
        root = tree.getroot()
        for synset in root.findall('synset'):
            sid = synset.get('id')
            definition = synset.get('definition', '')
            pos = POS_MAP.get(synset.get('part_of_speech', ''), 'u')

            synsets[sid] = {
                'id': sid,
                'ili': rwn_to_ili.get(sid, ''),
                'pos': pos,
                'definition': definition,
                'examples': [],
                'semfield': '',
                'relations': []
            }

            for sense in synset.findall('sense'):
                sense_text = sense.text
                if sense_text:
                    synset_senses[sid].append(sense_text.strip())

    lemma_data = defaultdict(list)

    for suffix in ['N', 'V', 'A']:
        tree = ET.parse(f'{raw_dir}/senses.{suffix}.xml')
        root = tree.getroot()
        for sense in root.findall('sense'):
            name = sense.get('name', '').strip()
            synset_id = sense.get('synset_id', '')
            pos = POS_MAP.get(sense.get('part_of_speech', ''), 'u')

            if name and synset_id and synset_id in synsets:
                key = (name, pos)
                if synset_id not in lemma_data[key]:
                    lemma_data[key].append(synset_id)

    for suffix in ['N', 'V', 'A']:
        tree = ET.parse(f'{raw_dir}/synset_relations.{suffix}.xml')
        root = tree.getroot()
        for rel in root.findall('relation'):
            rel_name = rel.get('name', '')
            parent_id = rel.get('parent_id', '')
            child_id = rel.get('child_id', '')

            lmf_rel = RELATION_MAP.get(rel_name, '')
            if lmf_rel and parent_id in synsets and child_id in synsets:
                synsets[parent_id]['relations'].append({
                    'target': child_id,
                    'relType': lmf_rel
                })

    lexical_entries = []
    for i, ((lemma, pos), senses) in enumerate(lemma_data.items()):
        lexical_entries.append({
            'id': i,
            'lemma': lemma,
            'pos': pos,
            'senses': senses
        })

    return {
        'meta': {
            'id': 'russian-ru',
            'label': 'Russian WordNet',
            'language': 'ru',
            'email': 'iga.masniak@ens.psl.eu',
            'license': 'https://creativecommons.org/licenses/by-nc-sa/4.0/',
            'version': '1.0',
            'dc:creator': 'Natalia Loukachevitch',
            'dc:contributor': 'Iga Masniak',
            'dc:description': 'Russian WordNet (RuWordNet) converted to GWA LMF format by Iga Masniak'
        },
        'synsets': list(synsets.values()),
        'lexical_entries': lexical_entries
    }


if __name__ == '__main__':
    result = convert_to_json()
    with open('data/jsons/RussianWordNet_standard.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=4, ensure_ascii=False)

    print('Done: RussianWordNet_standard.json')
    print(f"Synsets: {len(result['synsets'])}")
    print(f"Lexical entries: {len(result['lexical_entries'])}")
    print(f"With ILI: {sum(1 for s in result['synsets'] if s['ili'])}")
