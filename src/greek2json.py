import csv
import json
import os
import xml.etree.ElementTree as ET
from collections import defaultdict

from WordNetMapper import WordNetMapper

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_XML_PATH = os.path.join(_ROOT, 'data', 'raw', 'greek', 'wngre2.xml')
_DEFAULT_CILI_PATH = os.path.join(_ROOT, 'data', 'cili.tsv')
_DEFAULT_OUTPUT_PATH = os.path.join(_ROOT, 'data', 'jsons', 'GreekWordNet_standard.json')

my_mapper = WordNetMapper()

POS_MAP = {
    'n': 'n',
    'v': 'v',
    'a': 'a',
    'b': 'r',
}

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
    'verb_group': 'similar',
    'also_see': 'also',
    'near_antonym': 'antonym',
    'category_domain': 'domain_topic',
}


def _map_reltype(raw_type, unmapped_counts):
    if raw_type in VALID_RELTYPES:
        return raw_type
    if raw_type in RELATION_MAP:
        return RELATION_MAP[raw_type]
    unmapped_counts[raw_type] += 1
    return 'other'


def _load_ili_lookup(cili_path):
    pwn_2_ili = {}
    with open(cili_path, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            pwn_2_ili[row['origin'][8:16]] = row['ili_id']
    return pwn_2_ili


def _resolve_ili(eng20_id, pwn_2_ili):
    if not eng20_id.startswith('ENG20-'):
        return ''
    offset_20 = eng20_id.split('-')[1]
    try:
        offset_30, _pos = my_mapper.map_offset_to_offset(offset_20, '20', '30')
    except Exception:
        return ''
    return pwn_2_ili.get(offset_30, '')


def convert_to_json(xml_path=_DEFAULT_XML_PATH, cili_path=_DEFAULT_CILI_PATH, stats=None):

    pwn_2_ili = _load_ili_lookup(cili_path)

    tree = ET.parse(xml_path)
    root = tree.getroot()

    synsets = {}
    senses = []  # (lemma, pos, synset_id)
    skipped_placeholder = 0
    unmapped_reltypes = defaultdict(int)

    for syn_el in root.findall('SYNSET'):
        synset_id_raw = syn_el.findtext('ID')
        if not synset_id_raw:
            continue
        synset_id = synset_id_raw.strip()

        pos = POS_MAP.get(syn_el.findtext('POS') or '')
        if pos is None:
            continue

        ili = _resolve_ili(synset_id, pwn_2_ili)
        definition = (syn_el.findtext('DEF') or '').strip()

        relations = []
        for ilr in syn_el.findall('ILR'):
            target = (ilr.text or '').strip()
            type_el = ilr.find('TYPE')
            raw_rel_type = (type_el.text or '').strip() if type_el is not None else ''
            if target and raw_rel_type:
                rel_type = _map_reltype(raw_rel_type, unmapped_reltypes)
                relations.append({'target': target, 'relType': rel_type})

        synsets[synset_id] = {
            'id': synset_id,
            'ili': ili,
            'pos': pos,
            'definition': definition,
            'examples': [],
            'semfield': '',
            'relations': relations,
        }

        synonym_el = syn_el.find('SYNONYM')
        if synonym_el is None or synonym_el.find('LITERAL') is None:
            skipped_placeholder += 1
            continue

        for lit_el in synonym_el.findall('LITERAL'):
            lemma = (lit_el.text or '').strip()
            if lemma:
                senses.append((lemma, pos, synset_id))

    # Drop relations pointing at a synset id not present anywhere in
    # this file (WN-LMF's relation target is an IDREF and must resolve).
    known_ids = set(synsets.keys())
    dangling_dropped = 0
    for synset in synsets.values():
        kept = [r for r in synset['relations'] if r['target'] in known_ids]
        dangling_dropped += len(synset['relations']) - len(kept)
        synset['relations'] = kept

    # Group into lexical entries, one per (lemma, pos) pair.
    lemma_to_synsets = defaultdict(list)
    for lemma, pos, synset_id in senses:
        key = (lemma, pos)
        if synset_id not in lemma_to_synsets[key]:
            lemma_to_synsets[key].append(synset_id)

    lexical_entries = [
        {'id': i, 'lemma': lemma, 'pos': pos, 'senses': synset_ids}
        for i, ((lemma, pos), synset_ids) in enumerate(sorted(lemma_to_synsets.items()))
    ]

    output = {
        'meta': {
            'id': 'greek-el',
            'label': 'Greek WordNet',
            'language': 'el',
            'email': 'iga.masniak@ens.psl.eu',
            'license': '',
            'version': '20',
            'dc:creator': 'Lazaros Ioannidis',
            'dc:contributor': 'Iga Masniak',
            'dc:description': 'Greek WordNet converted to format by Iga Masniak',
        },
        'synsets': list(synsets.values()),
        'lexical_entries': lexical_entries,
    }

    if stats is not None:
        stats['skipped_placeholder'] = skipped_placeholder
        stats['unmapped_reltypes'] = dict(unmapped_reltypes)
        stats['dangling_dropped'] = dangling_dropped

    return output


if __name__ == '__main__':
    run_stats = {}
    data = convert_to_json(stats=run_stats)

    if run_stats['skipped_placeholder']:
        print(f"[greek2json] Note: {run_stats['skipped_placeholder']} synsets had no LITERAL "
              f"at all and contributed no lexical entries.")
    if run_stats['unmapped_reltypes']:
        print("[greek2json] Note: relTypes with no WN-LMF match, mapped to 'other':")
        for rel_type, count in sorted(run_stats['unmapped_reltypes'].items(), key=lambda kv: -kv[1]):
            print(f"    {rel_type}: {count}")
    if run_stats['dangling_dropped']:
        print(f"[greek2json] Note: {run_stats['dangling_dropped']} relation(s) dropped, "
              f"target synset not present anywhere in wngre2.xml.")

    os.makedirs(os.path.dirname(_DEFAULT_OUTPUT_PATH), exist_ok=True)
    with open(_DEFAULT_OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    n_synsets = len(data['synsets'])
    n_entries = len(data['lexical_entries'])
    n_with_ili = sum(1 for s in data['synsets'] if s['ili'])

    print(f'Done: {_DEFAULT_OUTPUT_PATH}')
    print(f'Synsets: {n_synsets}')
    print(f'Lexical entries: {n_entries}')
    print(f'With ILI: {n_with_ili} ({n_with_ili / n_synsets:.1%})')