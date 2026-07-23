import csv
import json
import os
from collections import defaultdict
from WordNetMapper import WordNetMapper
from nltk.corpus import wordnet as wn

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RELATION_MAP = {
    'hyponymOf': 'hypernym',
    'instanceOf': 'instance_hypernym',
    'partMeronymOf': 'mero_part',
    'partHolonymOf': 'holo_part',
    'memberMeronymOf': 'mero_member',
    'memberHolonymOf': 'holo_member',
    'madeofMeronymOf': 'mero_substance',
    'madeofHolonymOf': 'holo_substance',
    'locationMeronymOf': 'mero_location',
    'locationHolonymOf': 'holo_location',
    'nearAntonymOf': 'similar',
    'nearSynonymOf': 'similar',
    'domain': 'domain_topic',
    'concerns': 'domain_topic',
    'meronymOf': 'meronym',
    'roleAgent': 'co_agent_instrument',
    'rolePatient': 'co_patient_instrument',
    'involvedAgent': 'involved_agent',
    'involvedPatient': 'involved_patient',
    'involvedInstrument': 'involved_instrument',
    'madeBy': 'is_caused_by',
    'usedFor': 'instrument',
    'usedForObject': 'instrument',
}

POS_MAP = {
    'Noun': 'n',
    'Verb': 'v',
    'Adjective': 'a',
    'None': 'u'
}


def _load_ili_lookup(cili_path):
    pwn_2_ili = {}
    with open(cili_path, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            pwn_2_ili[row['origin'][8:16]] = row['ili_id']
    return pwn_2_ili


def _load_words(path):
    words = {}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 3:
                words[parts[0]] = {
                    'form': parts[1],
                    'pos': POS_MAP.get(parts[2], 'u')
                }
    return words


def _load_synsets(path):
    synsets = {}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 2:
                synsets[parts[0]] = {
                    'ontological_type': parts[1]
                }
    return synsets


def _load_wordsenses(path):
    wordsenses = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 3:
                wordsenses.append({
                    'wordsense_id': parts[0],
                    'word_id': parts[1],
                    'synset_id': parts[2]
                })
    return wordsenses


def _load_synset_domains(path):
    synset_domains = defaultdict(list)
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 3 and parts[1] == 'domain':
                synset_domains[parts[0]].append(parts[2])
    return synset_domains


def _load_relations(path, synsets, my_mapper, pwn_2_ili):
    synset_ili = {}
    synset_relations = defaultdict(list)

    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) < 4:
                continue
            synset_id = parts[0]
            rel_name = parts[1]
            target = parts[3]

            if rel_name == 'eqSynonymOf':
                if target.startswith('ENG20-'):
                    try:
                        eng_parts = target.split('-')
                        offset_20 = eng_parts[1]
                        pwn_offset, mapped_pos = my_mapper.map_offset_to_offset(offset_20, "20", "30")
                        ili = pwn_2_ili.get(pwn_offset, '')
                        if ili and synset_id not in synset_ili:
                            synset_ili[synset_id] = ili
                    except Exception:
                        pass
                elif '%' in target:
                    try:
                        lemma = wn.lemma_from_key(key=target)
                        synset = lemma.synset()
                        offset_30 = f'{synset.offset():08d}'
                        ili = pwn_2_ili.get(offset_30, '')
                        if ili and synset_id not in synset_ili:
                            synset_ili[synset_id] = ili
                    except Exception:
                        pass
            else:
                lmf_rel = RELATION_MAP.get(rel_name, '')
                if lmf_rel and target.isdigit() and target in synsets:
                    synset_relations[synset_id].append({
                        'target': target,
                        'relType': lmf_rel
                    })

    return synset_ili, synset_relations


def convert_to_json(raw_dir='data/raw/norwegian/dat', cili_path='data/cili.tsv'):
    """
    Convert Norwegian WordNet raw .tab files into the standard GWA
    LMF-style dict used across all converters in this project.

    Parameters
    ----------
    raw_dir : str
        Directory containing words.tab, synsets.tab, wordsenses.tab,
        synset_attributes.tab, relations.tab
    cili_path : str
        Path to the cili.tsv ILI lookup file

    Returns
    -------
    dict with keys: 'meta', 'synsets', 'lexical_entries'
    """
    my_mapper = WordNetMapper()
    pwn_2_ili = _load_ili_lookup(cili_path)

    words = _load_words(f'{raw_dir}/words.tab')
    synsets = _load_synsets(f'{raw_dir}/synsets.tab')
    wordsenses = _load_wordsenses(f'{raw_dir}/wordsenses.tab')
    synset_domains = _load_synset_domains(f'{raw_dir}/synset_attributes.tab')
    synset_ili, synset_relations = _load_relations(
        f'{raw_dir}/relations.tab', synsets, my_mapper, pwn_2_ili
    )

    synset_pos = {}
    for ws in wordsenses:
        word_id = ws['word_id']
        synset_id = ws['synset_id']
        if word_id in words and synset_id in synsets:
            if synset_id not in synset_pos:
                synset_pos[synset_id] = words[word_id]['pos']

    synsets_list = []
    for sid in synsets:
        domain = '; '.join(synset_domains.get(sid, []))
        relations = synset_relations.get(sid, [])

        synsets_list.append({
            'id': sid,
            'ili': synset_ili.get(sid, ''),
            'pos': synset_pos.get(sid, 'n'),
            'definition': '',
            'examples': [],
            'semfield': domain,
            'relations': relations
        })

    lemma_to_synsets = defaultdict(list)
    lemma_to_pos = {}

    for ws in wordsenses:
        word_id = ws['word_id']
        synset_id = ws['synset_id']
        if word_id in words and synset_id in synsets:
            word = words[word_id]
            key = (word['form'], word['pos'])
            if synset_id not in lemma_to_synsets[key]:
                lemma_to_synsets[key].append(synset_id)
            lemma_to_pos[key] = word['pos']

    lexical_entries = []
    for i, ((lemma, pos), senses) in enumerate(lemma_to_synsets.items()):
        lexical_entries.append({
            'id': i,
            'lemma': lemma,
            'pos': pos,
            'senses': senses
        })

    return {
        'meta': {
            'id': 'norwegian-nor',
            'label': 'Norwegian WordNet',
            'language': 'nor',
            'email': 'iga.masniak@ens.psl.eu',
            'license': 'https://creativecommons.org/licenses/by-nc-sa/4.0/',
            'version': '1.0',
            'dc:creator': 'Arne Martinus Lindstad',
            'dc:contributor': 'Iga Masniak',
            'dc:description': 'Norwegian WordNet converted to GWA LMF format by Iga Masniak'
        },
        'synsets': synsets_list,
        'lexical_entries': lexical_entries
    }


if __name__ == '__main__':
    result = convert_to_json()
    with open('data/jsons/NorwegianWordNet_standard.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=4, ensure_ascii=False)

    print('Done: NorwegianWordNet_standard.json')
    print(f"Synsets: {len(result['synsets'])}")
    print(f"With ILI: {sum(1 for s in result['synsets'] if s['ili'])}")