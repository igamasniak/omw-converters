import csv
import os
import json
import re
from collections import defaultdict

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

POS_MAP = {
    'n': 'n',
    'v': 'v',
    'a': 'a',
    's': 's',
    'r': 'r'
}

WN_RELATIONS = {
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
}


def _load_ili_lookup(cili_path):
    pwn_2_ili = {}
    with open(cili_path, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            pwn_2_ili[row['origin'][8:16]] = row['ili_id']
    return pwn_2_ili


def _load_wn31_to_wn30(mapping_path):
    with open(mapping_path, 'r', encoding='utf-8') as f:
        mapping_data = json.load(f)
    return mapping_data[0]['synset-mapping']


def _extract_relations(block_text):
    relations = []
    for wn_rel, lmf_rel in WN_RELATIONS.items():
        pattern = re.escape(wn_rel) + r'\s+(.*?)(?:\s*[;.])'
        matches = re.findall(pattern, block_text)
        for match in matches:
            for t in match.split(','):
                t = t.strip()
                if t.startswith('wordnetSynset:'):
                    t = t[len('wordnetSynset:'):]
                t = t.rstrip(' .,;')
                if re.match(r'\d{8}-[a-z]', t):
                    relations.append({'target': t, 'relType': lmf_rel})
    return relations


def _process_lexical_entry_block(first_line, block_text, entries):
    m = re.match(r'wordnetLexicalEntry:(\S+)\s+a\s+ontolex:LexicalEntry', first_line)
    if not m:
        return
    eid = m.group(1)
    label_m = re.search(r'rdfs:label\s+"([^"]*)"', block_text)
    label = label_m.group(1) if label_m else ''
    synset_ids = []
    for s in re.findall(r'wordnetSynset:(\S+)', block_text):
        s = s.rstrip(' .,;')
        if re.match(r'\d{8}-[a-z]', s):
            if s not in synset_ids:
                synset_ids.append(s)
    entries[eid] = {'label': label, 'synsets': synset_ids}


def _process_synset_block(first_line, block_text, synsets):
    m = re.match(r'wordnetSynset:(\S+)\s+a\s+ontolex:LexicalConcept', first_line)
    if not m:
        return
    sid = m.group(1)
    def_m = re.search(r'skos:definition\s+"((?:[^"\\]|\\.)*)"', block_text)
    definition = def_m.group(1) if def_m else ''
    relations = _extract_relations(block_text)
    synsets[sid] = {'definition': definition, 'relations': relations}


def _parse_ttl(ttl_path):
    entries = {}
    synsets = {}
    current_block = []

    with open(ttl_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.rstrip()
            if line == '' and current_block:
                first_line = current_block[0]
                block_text = '\n'.join(current_block)

                _process_lexical_entry_block(first_line, block_text, entries)
                _process_synset_block(first_line, block_text, synsets)

                current_block = []

            if line.strip():
                current_block.append(line)

    # Process last block
    if current_block:
        first_line = current_block[0]
        block_text = '\n'.join(current_block)
        _process_synset_block(first_line, block_text, synsets)

    return entries, synsets


def convert_to_json(ttl_path='data/raw/latin_revised/lwn31.ttl',
                     mapping_path='data/mapping_wordnet.json',
                     cili_path='data/cili.tsv'):
    """
    Convert the revised Latin WordNet (LiLa TTL, wn 3.1) into the standard
    GWA LMF-style dict used across all converters in this project.

    Parameters
    ----------
    ttl_path : str
        Path to the lwn31.ttl file
    mapping_path : str
        Path to the mapping_wordnet.json (wn 3.1 -> wn 3.0 synset mapping)
    cili_path : str
        Path to the cili.tsv ILI lookup file

    Returns
    -------
    dict with keys: 'meta', 'synsets', 'lexical_entries'
    """
    pwn_2_ili = _load_ili_lookup(cili_path)
    wn31_to_wn30 = _load_wn31_to_wn30(mapping_path)
    entries, synsets = _parse_ttl(ttl_path)

    # ILI mapping: 3.1 -> 3.0 -> cili
    synset_ili = {}
    for sid in synsets:
        offset = sid.split('-')[0]
        pos = sid.split('-')[1]

        # Build 3.1 key: pos + offset without leading zeros
        key_31 = pos + offset.lstrip('0')
        val_30 = wn31_to_wn30.get(key_31, '')

        if val_30:
            # Value is like "n08936605" -> offset is characters 1-9
            offset_30 = val_30[1:9]
            ili = pwn_2_ili.get(offset_30, '')
        else:
            # Fallback: try direct lookup (some offsets unchanged between versions)
            ili = pwn_2_ili.get(offset, '')

        if ili:
            synset_ili[sid] = ili

    # Build synsets list
    synsets_list = []
    for sid, data in synsets.items():
        pos = POS_MAP.get(sid.split('-')[1], 'u')
        # Filter relations to only target existing synsets
        valid_relations = [r for r in data['relations'] if r['target'] in synsets]

        synsets_list.append({
            'id': sid,
            'ili': synset_ili.get(sid, ''),
            'pos': pos,
            'definition': data['definition'],
            'examples': [],
            'semfield': '',
            'relations': valid_relations
        })

    # Build lexical entries
    lemma_to_synsets = defaultdict(list)

    for eid, data in entries.items():
        label = data['label']
        for sid in data['synsets']:
            if sid in synsets and sid not in lemma_to_synsets[label]:
                lemma_to_synsets[label].append(sid)

    lexical_entries = []
    for i, (lemma, senses) in enumerate(lemma_to_synsets.items()):
        # Get POS from first synset
        pos = POS_MAP.get(senses[0].split('-')[1], 'n') if senses else 'n'
        lexical_entries.append({
            'id': i,
            'lemma': lemma,
            'pos': pos,
            'senses': senses
        })

    return {
        'meta': {
            'id': 'latin-revised-la',
            'label': 'Latin WordNet (Revision)',
            'language': 'la',
            'email': 'iga.masniak@ens.psl.eu',
            'license': 'CC BY SA',
            'version': '3.1',
            'dc:creator': 'Eleonora Litta, Greta Franzini, Giulia Pedonese, Marco Passarotti',
            'dc:contributor': 'Iga Masniak',
            'dc:description': 'Latin WordNet Revision converted to GWA LMF format by Iga Masniak'
        },
        'synsets': synsets_list,
        'lexical_entries': lexical_entries
    }


if __name__ == '__main__':
    result = convert_to_json()
    with open('data/jsons/LatinWordNet_revised_standard.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=4, ensure_ascii=False)

    print('Done: LatinWordNet_revised_standard.json')
    print(f"Synsets: {len(result['synsets'])}")
    print(f"Lexical entries: {len(result['lexical_entries'])}")
    print(f"With ILI: {sum(1 for s in result['synsets'] if s['ili'])}")
    print(f"Total relations: {sum(len(s['relations']) for s in result['synsets'])}")