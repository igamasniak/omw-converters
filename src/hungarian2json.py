import os
import xml.etree.ElementTree as ET

from src.common import IliResolver, build_output, make_synset, save_output

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RAW_PATH = 'data/raw/hungarian/huwn.xml'

POS_MAP = {'n': 'n', 'v': 'v', 'a': 'a', 'b': 'r'}

VALID_RELTYPES = frozenset({
    'agent', 'also', 'attribute', 'be_in_state', 'causes', 'classified_by',
    'classifies', 'co_agent_instrument', 'co_agent_patient', 'co_agent_result',
    'co_instrument_agent', 'co_instrument_patient', 'co_instrument_result',
    'co_patient_agent', 'co_patient_instrument', 'co_result_agent',
    'co_result_instrument', 'co_role', 'direction', 'domain_region',
    'domain_topic', 'exemplifies', 'entails', 'eq_synonym',
    'has_domain_region', 'has_domain_topic', 'is_exemplified_by',
    'holo_location', 'holo_member', 'holo_part', 'holo_portion',
    'holo_substance', 'holonym', 'hypernym', 'hyponym', 'in_manner',
    'instance_hypernym', 'instance_hyponym', 'instrument', 'involved',
    'involved_agent', 'involved_direction', 'involved_instrument',
    'involved_location', 'involved_patient', 'involved_result',
    'involved_source_direction', 'involved_target_direction', 'is_caused_by',
    'is_entailed_by', 'location', 'manner_of', 'mero_location', 'mero_member',
    'mero_part', 'mero_portion', 'mero_substance', 'meronym', 'similar',
    'other', 'patient', 'restricted_by', 'restricts', 'result', 'role',
    'source_direction', 'state_of', 'target_direction', 'subevent',
    'is_subevent_of', 'antonym', 'feminine', 'has_feminine', 'masculine',
    'has_masculine', 'young', 'has_young', 'diminutive', 'has_diminutive',
    'augmentative', 'has_augmentative', 'anto_gradable', 'anto_simple',
    'anto_converse', 'ir_synonym',
})

RELATION_MAP = {
    'similar_to': 'similar',
    'near_synonym': 'similar',
    'verb_group': 'similar',
    'also_see': 'also',
    'near_antonym': 'antonym',
    'converse': 'anto_converse',
    'category_domain': 'domain_topic',
    'category_member': 'has_domain_topic',
    'region_domain': 'domain_region',
    'region_member': 'has_domain_region',
    'subevent_of': 'is_subevent_of',
    'subevent_nec_of': 'is_subevent_of',
    'has_subevent': 'subevent',
    'is_preparatory_phase_of': 'is_subevent_of',
    'has_preparatory_phase': 'subevent',
    'caused_by': 'is_caused_by',
    'is_consequent_state_of': 'is_caused_by',
    'has_consequence': 'causes',
    'has_consequent_state': 'causes',
}

META = {
    'id': 'hungarian-hu',
    'label': 'Hungarian WordNet',
    'language': 'hu',
    'email': 'iga.masniak@ens.psl.eu',
    'license': 'CC BY-SA 4.0',
    'version': '1.0',
    'dc:creator': 'Mihaltz Marton',
    'dc:contributor': 'Iga Masniak',
    'dc:description': 'Hungarian WordNet converted to GWA LMF format by Iga Masniak'
}


def map_reltype(raw_type):
    if raw_type in VALID_RELTYPES:
        return raw_type
    return RELATION_MAP.get(raw_type, 'other')


def read_relations(syn):
    relations = []
    for ilr in syn.findall('ILR'):
        target, rel_type = (ilr.text or '').strip(), (ilr.findtext('TYPE') or '').strip()
        if target and rel_type:
            relations.append({'target': target, 'relType': map_reltype(rel_type)})
    return relations


def read_source(path):
    return ET.parse(path).getroot().findall('SYNSET')


def convert_to_json(raw_path=RAW_PATH, cili_path='data/cili.tsv'):
    ili = IliResolver(cili_path)
    synsets, senses = {}, []

    for syn in read_source(raw_path):
        synset_id = (syn.findtext('ID') or '').strip()
        pos = POS_MAP.get(syn.findtext('POS') or '')
        if not synset_id or not pos:
            continue

        id3 = syn.findtext('ID3') or ''
        offset = id3.split('-')[1] if id3.startswith('ENG30-') else ''
        synsets[synset_id] = make_synset(synset_id, pos, ili.get(offset, pos, '30'),
                                         syn.findtext('DEF') or '', [syn.findtext('USAGE')],
                                         syn.findtext('DOMAIN') or '', read_relations(syn))

        if (syn.findtext('NL') or '').strip().lower() != 'yes':
            senses += [(lit.text, pos, synset_id) for lit in syn.findall('SYNONYM/LITERAL')]

    for synset in synsets.values():
        synset['relations'] = [r for r in synset['relations'] if r['target'] in synsets]

    return build_output(META, synsets, senses)


if __name__ == '__main__':
    save_output(convert_to_json(), 'HungarianWordNet')