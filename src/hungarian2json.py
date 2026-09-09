
import csv
import json
import os
import xml.etree.ElementTree as ET
from collections import defaultdict

# Anchor default paths to the project root regardless of the working
# directory the script is run from (src/, an IDE, or via run.py).
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_XML_PATH = os.path.join(_ROOT, 'data', 'raw', 'hungarian', 'huwn.xml')
_DEFAULT_CILI_PATH = os.path.join(_ROOT, 'data', 'cili.tsv')
_DEFAULT_OUTPUT_PATH = os.path.join(_ROOT, 'data', 'jsons', 'HungarianWordNet_standard.json')

POS_MAP = {
    'n': 'n',
    'v': 'v',
    'a': 'a',
    'b': 'r',
}

# The full relType enumeration allowed by WN-LMF's SynsetRelation (from the
# DTD). Anything not in here, and not in RELATION_MAP below, gets 'other'.
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

# BalkaNet ILR TYPE values that aren't valid WN-LMF relTypes, mapped to the
# closest available one. Reviewed against huwn.xml's actual TYPE values;
# anything not covered here falls back to 'other' (see convert_to_json).
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


def _literal_text(lit_el):
    """Text of a LITERAL element is whatever precedes its first child
    (SENSE/LNOTE), which is exactly what ElementTree puts in .text."""
    return (lit_el.text or '').strip()


def convert_to_json(xml_path=_DEFAULT_XML_PATH, cili_path=_DEFAULT_CILI_PATH, stats=None):

    pwn_2_ili = _load_ili_lookup(cili_path)

    tree = ET.parse(xml_path)
    root = tree.getroot()

    synsets = {}
    # (lemma, pos, synset_id) triples, one per LITERAL occurrence
    senses = []

    skipped_placeholder = 0
    missing_pos = 0
    unmapped_reltypes = defaultdict(int)

    for syn_el in root.findall('SYNSET'):
        synset_id = syn_el.findtext('ID')
        if not synset_id:
            continue

        raw_pos = syn_el.findtext('POS') or ''
        pos = POS_MAP.get(raw_pos)
        if pos is None:
            missing_pos += 1
            continue

        id3 = syn_el.findtext('ID3') or ''
        ili = ''
        if id3.startswith('ENG30-'):
            offset = id3.split('-')[1]
            ili = pwn_2_ili.get(offset, '')

        definition = (syn_el.findtext('DEF') or '').strip()

        usage = syn_el.findtext('USAGE')
        examples = [usage.strip()] if usage and usage.strip() else []

        domain = (syn_el.findtext('DOMAIN') or '').strip()

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
            'examples': examples,
            'semfield': domain,
            'relations': relations,
        }

        is_placeholder = (syn_el.findtext('NL') or '').strip().lower() == 'yes'
        if is_placeholder:
            skipped_placeholder += 1
            continue

        synonym_el = syn_el.find('SYNONYM')
        if synonym_el is not None:
            for lit_el in synonym_el.findall('LITERAL'):
                lemma = _literal_text(lit_el)
                if lemma:
                    senses.append((lemma, pos, synset_id))

    # Second pass: drop relations that point at a synset id not present
    # anywhere in this file. WN-LMF's SynsetRelation target is an IDREF,
    # so a dangling target fails DTD validation even though it's harmless
    # data-wise (this affects a single relation in huwn.xml as of writing).
    known_ids = set(synsets.keys())
    dangling_dropped = 0
    for synset in synsets.values():
        kept = [r for r in synset['relations'] if r['target'] in known_ids]
        dangling_dropped += len(synset['relations']) - len(kept)
        synset['relations'] = kept

    # Group senses into lexical entries, one per (lemma, pos) pair, each
    # listing every synset it belongs to.
    lemma_to_synsets = defaultdict(list)
    for lemma, pos, synset_id in senses:
        key = (lemma, pos)
        if synset_id not in lemma_to_synsets[key]:
            lemma_to_synsets[key].append(synset_id)

    lexical_entries = [
        {
            'id': i,
            'lemma': lemma,
            'pos': pos,
            'senses': synset_ids,
        }
        for i, ((lemma, pos), synset_ids) in enumerate(sorted(lemma_to_synsets.items()))
    ]

    output = {
        'meta': {
            'id': 'hungarian-hu',
            'label': 'Hungarian WordNet',
            'language': 'hu',
            'email': 'iga.masniak@ens.psl.eu',
            'license': '',
            'version': '',
            'dc:creator': 'Mihaltz Marton',
            'dc:contributor': 'Iga Masniak',
            'dc:description': 'Hungarian WordNet converted to GWA LMF format by Iga Masniak',
        },
        'synsets': list(synsets.values()),
        'lexical_entries': lexical_entries,
    }

    if stats is not None:
        stats['missing_pos'] = missing_pos
        stats['skipped_placeholder'] = skipped_placeholder
        stats['unmapped_reltypes'] = dict(unmapped_reltypes)
        stats['dangling_dropped'] = dangling_dropped

    return output


if __name__ == '__main__':
    run_stats = {}
    data = convert_to_json(stats=run_stats)

    if run_stats['missing_pos']:
        print(f"[hungarian2json] Note: {run_stats['missing_pos']} synsets skipped, unrecognised POS.")
    if run_stats['skipped_placeholder']:
        print(f"[hungarian2json] Note: {run_stats['skipped_placeholder']} synsets had a placeholder "
              f"LITERAL (NL=yes) and contributed no lexical entries.")
    if run_stats['unmapped_reltypes']:
        print("[hungarian2json] Note: relTypes with no WN-LMF match, mapped to 'other':")
        for rel_type, count in sorted(run_stats['unmapped_reltypes'].items(), key=lambda kv: -kv[1]):
            print(f"    {rel_type}: {count}")
    if run_stats['dangling_dropped']:
        print(f"[hungarian2json] Note: {run_stats['dangling_dropped']} relation(s) dropped, "
              f"target synset not present anywhere in huwn.xml.")

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