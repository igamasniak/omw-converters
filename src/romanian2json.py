import os
import pickle
import re

from src.common import IliResolver, build_output, make_synset, save_output

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RAW_PATH = 'data/raw/romanian/rowordnet.pickle'

RELATION_MAP = {
    'hypernym': 'hypernym',
    'hyponym': 'hyponym',
    'instance_hypernym': 'instance_hypernym',
    'instance_hyponym': 'instance_hyponym',
    'part_holonym': 'holo_part',
    'part_meronym': 'mero_part',
    'member_holonym': 'holo_member',
    'member_meronym': 'mero_member',
    'substance_holonym': 'holo_substance',
    'substance_meronym': 'mero_substance',
    'entailment': 'entails',
    'cause': 'causes',
    'similar_to': 'similar',
    'attribute': 'attribute',
    'also_see': 'also',
    'verb_group': 'similar',
    'domain_TOPIC': 'domain_topic',
    'domain_REGION': 'domain_region',
    'domain_USAGE': 'exemplifies',
    'domain_member_TOPIC': 'has_domain_topic',
    'domain_member_REGION': 'has_domain_region',
    'domain_member_USAGE': 'is_exemplified_by',
    'near_antonym': 'antonym',
    'near_also_see': 'also',
    'near_verb_group': 'similar',
    'near_domain_TOPIC': 'domain_topic',
    'near_domain_REGION': 'domain_region',
    'near_domain_USAGE': 'exemplifies',
    'near_domain_member_TOPIC': 'has_domain_topic',
    'near_domain_member_REGION': 'has_domain_region',
    'near_domain_member_USAGE': 'is_exemplified_by',
}

META = {
    'id': 'romanian-ro',
    'label': 'RoWordNet',
    'language': 'ro',
    'email': 'iga.masniak@ens.psl.eu',
    'license': 'https://opensource.org/licenses/MIT',
    'version': '1.1',
    'dc:creator': 'Dan Tufiș, Verginica Barbu Mititelu',
    'dc:contributor': 'Iga Masniak',
    'dc:source': 'Tufiș & Barbu Mititelu (2014), The Lexical Ontology for Romanian, Springer; '
                 'Dumitrescu et al. (2018), RoWordNet - A Python API for the Romanian WordNet, IEEE ECAI',
    'dc:description': 'Romanian WordNet (RoWordNet) converted to GWA LMF format by Iga Masniak'
}


def split_definition_examples(text):
    if not text:
        return '', []
    paren_quotes = {q.strip() for m in re.finditer(r'\([^)]*"[^)]*\)', text)
                    for q in re.findall(r'"\s*(.*?)\s*"', m.group())}
    examples = [p.strip() for p in re.findall(r'"\s*(.*?)\s*"', text)
                if p.strip() and p.strip() not in paren_quotes and len(p.strip()) >= 15]
    definition = text
    for example in examples:
        definition = re.sub(r'\s*;\s*"\s*' + re.escape(example) + r'\s*"\s*', '', definition)
        definition = re.sub(r'"\s*' + re.escape(example) + r'\s*"', '', definition)
    definition = re.sub(r'\s*;\s*;', ';', re.sub(r'\s*;\s*$', '', definition))
    return definition.strip().rstrip(';').rstrip('.').strip(), examples


def clean_lemma(literal):
    return literal.replace('_', ' ').replace('|', '')


def read_source(path):
    with open(path, 'rb') as f:
        return pickle.load(f)


def convert_to_json(raw_path=RAW_PATH, cili_path='data/cili.tsv'):
    ili = IliResolver(cili_path)
    wn = read_source(raw_path)
    synset_ids = set(wn.synsets())
    synsets, senses = {}, []

    for synset_id in wn.synsets():
        s = wn.synset(synset_id)
        parts = synset_id.split('-')
        pos = str(s.pos)
        synset_ili = ''
        if parts[0] == 'ENG30':
            pos = ili.pwn_pos(parts[1], pos)
            synset_ili = ili.get(parts[1], pos, '30')

        relations = [{'target': target, 'relType': RELATION_MAP[rel]}
                     for target, rel in wn.outbound_relations(synset_id)
                     if rel in RELATION_MAP and target in synset_ids]
        definition, examples = split_definition_examples(s.definition)
        semfield = s.domain if s.domain and s.domain != 'factotum' else ''

        synsets[synset_id] = make_synset(synset_id, pos, synset_ili, definition, examples, semfield, relations)
        senses += [(clean_lemma(literal), pos, synset_id) for literal in s.literals if literal]

    return build_output(META, synsets, senses)


if __name__ == '__main__':
    save_output(convert_to_json(), 'RomanianWordNet')