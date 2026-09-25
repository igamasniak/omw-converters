import csv
import os
import json
import pickle
import re
from collections import defaultdict

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Relation type mapping
SYNSET_REL_MAP = {
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
    'near_eng_derivat': 'similar',
    'near_derived_from': 'similar',
    'near_pertainym': 'similar',
    'near_also_see': 'also',
    'near_verb_group': 'similar',
    'near_participle': 'similar',
    'near_domain_TOPIC': 'domain_topic',
    'near_domain_REGION': 'domain_region',
    'near_domain_USAGE': 'exemplifies',
    'near_domain_member_TOPIC': 'has_domain_topic',
    'near_domain_member_REGION': 'has_domain_region',
    'near_domain_member_USAGE': 'is_exemplified_by',
}


def _load_ili_lookup(cili_path):
    pwn_2_ili = {}
    with open(cili_path, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            pwn_2_ili[row['origin'][8:16]] = row['ili_id']
    return pwn_2_ili


def split_definition_examples(text):
    if not text:
        return '', []

    # Find quoted parts inside parentheses — keep in definition
    paren_quotes = set()
    for m in re.finditer(r'\([^)]*"[^)]*\)', text):
        for q in re.findall(r'"\s*(.*?)\s*"', m.group()):
            paren_quotes.add(q.strip())

    # Find all quoted parts
    quoted_parts = re.findall(r'"\s*(.*?)\s*"', text)

    examples = []
    for part in quoted_parts:
        part = part.strip()
        if not part:
            continue
        # Skip if inside parentheses or too short to be an example
        if part in paren_quotes or len(part) < 15:
            continue
        examples.append(part)

    # Remove only the extracted examples from the text
    definition = text
    for ex in examples:
        definition = re.sub(r'\s*;\s*"\s*' + re.escape(ex) + r'\s*"\s*', '', definition)
        definition = re.sub(r'"\s*' + re.escape(ex) + r'\s*"', '', definition)

    # Clean up
    definition = re.sub(r'\s*;\s*$', '', definition)
    definition = re.sub(r'\s*;\s*;', ';', definition)
    definition = re.sub(r'\s+', ' ', definition)
    definition = definition.strip().rstrip(';').rstrip('.').strip()

    return definition, examples


def convert_to_json(raw_pickle_path='data/raw/romanian/rowordnet.pickle', cili_path='data/cili.tsv'):
    """
    Convert Romanian WordNet (RoWordNet) raw pickle into the standard
    GWA LMF-style dict used across all converters in this project.

    Parameters
    ----------
    raw_pickle_path : str
        Path to the rowordnet.pickle file
    cili_path : str
        Path to the cili.tsv ILI lookup file

    Returns
    -------
    dict with keys: 'meta', 'synsets', 'lexical_entries'
    """
    pwn_2_ili = _load_ili_lookup(cili_path)

    with open(raw_pickle_path, 'rb') as f:
        wn = pickle.load(f)

    synsets = {}
    senses = []
    all_offsets = set()

    # First pass: collect all synset offsets
    for sid in wn.synsets():
        s = wn.synset(sid)
        parts = s.id.split('-')
        offset = parts[1]
        all_offsets.add(offset)

    # Second pass: build synsets and senses
    for sid in wn.synsets():
        s = wn.synset(sid)

        parts = s.id.split('-')
        offset = parts[1]
        pos = parts[2] if len(parts) >= 3 else 'u'

        # ILI lookup
        ili = pwn_2_ili.get(offset, '')

        # Relations (only keep those targeting existing synsets)
        synset_relations = []
        for target_id, rel_type in wn.outbound_relations(sid):
            target_parts = target_id.split('-')
            target_offset = target_parts[1]

            if rel_type in SYNSET_REL_MAP and target_offset in all_offsets:
                synset_relations.append({
                    'target': target_offset,
                    'relType': SYNSET_REL_MAP[rel_type]
                })

        # Domain as semfield
        domain = s.domain if s.domain and s.domain != 'factotum' else ''

        # Split definition and examples
        definition, examples = split_definition_examples(s.definition if s.definition else '')

        # Store synset
        synsets[offset] = {
            'id': offset,
            'ili': ili,
            'pos': pos,
            'definition': definition,
            'examples': examples,
            'semfield': domain,
            'relations': synset_relations
        }

        # Store senses
        for lemma in s.literals:
            if lemma:
                senses.append((offset, lemma))

    # Build lexical entries
    lemma_to_synsets = defaultdict(list)
    for offset, lemma in senses:
        if offset not in lemma_to_synsets[lemma]:
            lemma_to_synsets[lemma].append(offset)

    return {
        'meta': {
            'id': 'romanian-ro',
            'label': 'RoWordNet',
            'language': 'ro',
            'email': 'iga.masniak@ens.psl.eu',
            'license': 'MIT License',
            'version': '',
            'dc:creator': 'Dan Tufiș, Verginica Barbu Mititelu',
            'dc:contributor': 'Iga Masniak',
            'dc:source': 'Tufiș & Barbu Mititelu (2014), The Lexical Ontology for Romanian, Springer; '
                          'Dumitrescu et al. (2018), RoWordNet - A Python API for the Romanian WordNet, IEEE ECAI',
            'dc:description': 'Romanian WordNet (RoWordNet) converted to GWA LMF format by Iga Masniak'
        },
        'synsets': list(synsets.values()),
        'lexical_entries': [
            {'id': i, 'lemma': l, 'senses': s} for i, (l, s) in enumerate(lemma_to_synsets.items())
        ]
    }


if __name__ == '__main__':
    result = convert_to_json()
    with open('data/jsons/RomanianWordNet_standard.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=4, ensure_ascii=False)

    print('Done: RomanianWordNet_standard.json')
    print(f"Synsets: {len(result['synsets'])}")
    print(f"Lexical entries: {len(result['lexical_entries'])}")