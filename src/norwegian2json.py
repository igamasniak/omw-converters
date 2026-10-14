import os
from collections import defaultdict

from nltk.corpus import wordnet as wn

from src.common import IliResolver, build_output, make_synset, save_output

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RAW_DIR = 'data/raw/norwegian/dat'

POS_MAP = {'Noun': 'n', 'Verb': 'v', 'Adjective': 'a'}

RELATION_MAP = {
    'hyponymOf': 'hypernym',
    'instanceOf': 'instance_hypernym',
    'partHolonymOf': 'mero_part',
    'partMeronymOf': 'holo_part',
    'memberHolonymOf': 'mero_member',
    'memberMeronymOf': 'holo_member',
    'madeofHolonymOf': 'mero_substance',
    'madeofMeronymOf': 'holo_substance',
    'locationHolonymOf': 'mero_location',
    'locationMeronymOf': 'holo_location',
    'meronymOf': 'holonym',
    'nearSynonymOf': 'similar',
    'xposNearSynonymOf': 'similar',
    'nearAntonymOf': 'antonym',
    'domain': 'domain_topic',
    'concerns': 'domain_topic',
    'roleAgent': 'agent',
    'rolePatient': 'patient',
    'involvedAgent': 'involved_agent',
    'involvedPatient': 'involved_patient',
    'involvedInstrument': 'involved_instrument',
    'madeBy': 'is_caused_by',
    'usedFor': 'instrument',
    'usedForObject': 'instrument',
}

META = {
    'id': 'norwegian-nb',
    'label': 'Norwegian Wordnet - Bokmål',
    'language': 'nb',
    'email': 'iga.masniak@ens.psl.eu',
    'license': 'https://creativecommons.org/licenses/by-nc-sa/4.0/',
    'version': '1.1.2',
    'dc:creator': 'Arne Martinus Lindstad',
    'dc:contributor': 'Iga Masniak',
    'dc:description': 'Norwegian Wordnet - Bokmål converted to GWA LMF format by Iga Masniak'
}


def read_tab(raw_dir, name):
    with open(f'{raw_dir}/{name}', encoding='utf-8') as f:
        return [line.rstrip('\n').split('\t') for line in f if line.strip()]


def eq_ili(target, ili):
    if target.startswith('ENG20-'):
        _, offset, pos = target.split('-')
        return ili.get(offset, pos, '20')
    if '%' in target:
        try:
            synset = wn.lemma_from_key(target).synset()
        except Exception:
            return ''
        return ili.get(synset.offset(), synset.pos(), '30')
    return ''


def read_source(raw_dir):
    words = {r[0]: (r[1], POS_MAP.get(r[2], 'u')) for r in read_tab(raw_dir, 'words.tab') if len(r) >= 3}
    synset_ids = {r[0] for name in ('synsets.tab', 'dummies.tab') for r in read_tab(raw_dir, name)}
    wordsenses = [(r[1], r[2]) for r in read_tab(raw_dir, 'wordsenses.tab')
                  if len(r) >= 3 and r[1] in words and r[2] in synset_ids]
    domains = defaultdict(list)
    for r in read_tab(raw_dir, 'synset_attributes.tab'):
        if len(r) >= 3 and r[1] == 'domain':
            domains[r[0]].append(r[2])
    relations = [r for r in read_tab(raw_dir, 'relations.tab') if len(r) >= 4]
    return words, wordsenses, domains, relations


def convert_to_json(raw_dir=RAW_DIR, cili_path='data/cili.tsv'):
    ili = IliResolver(cili_path)
    words, wordsenses, domains, relations = read_source(raw_dir)

    senses = [(words[word_id][0], words[word_id][1], synset_id) for word_id, synset_id in wordsenses]
    synset_pos = {}
    for _, pos, synset_id in senses:
        if synset_pos.get(synset_id, 'u') == 'u':
            synset_pos[synset_id] = pos

    synset_ili, synset_relations = {}, defaultdict(list)
    for synset_id, name, _, target, *_ in relations:
        if synset_id not in synset_pos:
            continue
        if name == 'eqSynonymOf':
            if not synset_ili.get(synset_id):
                synset_ili[synset_id] = eq_ili(target, ili)
        elif name in RELATION_MAP and target in synset_pos:
            relation = {'target': target, 'relType': RELATION_MAP[name]}
            if relation not in synset_relations[synset_id]:
                synset_relations[synset_id].append(relation)

    synsets = {
        synset_id: make_synset(synset_id, pos, synset_ili.get(synset_id, ''),
                               semfield='; '.join(domains.get(synset_id, [])),
                               relations=synset_relations[synset_id])
        for synset_id, pos in synset_pos.items()
    }
    return build_output(META, synsets, senses)


if __name__ == '__main__':
    save_output(convert_to_json(), 'NorwegianWordNet')