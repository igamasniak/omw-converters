import json
import os
import re
from collections import defaultdict

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# TatWordNet is a 120 MB Turtle (RDF) file. Loading it with rdflib takes minutes and several GB of RAM,
# so this converter reads it block by block instead: every resource in the file is one block
# separated by an empty line, starting with "<subject> a type ;" and then one "\tpredicate object ;" per line.

BASE = 'http://lod.wordnet.tatar/'

POS_MAP = {
    'wn:noun': 'n',
    'wn:verb': 'v',
    'wn:adjective': 'a',
}

# Matches one object on a line: "literal"@lang, <uri> or prefix:name
OBJECT_RE = re.compile(r'"((?:[^"\\]|\\.)*)"(?:@([\w-]+))?|<([^>]*)>|([A-Za-z]+:[\w-]+)')


def clean_text(text):
    if not text:
        return text
    text = text.replace('\\"', '"').replace('\\\\', '\\')
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def local_id(uri, kind):
    """<http://lod.wordnet.tatar/synset/9539-N> -> '9539-N'"""
    return uri[len(BASE + kind + '/'):]


def parse_block(block):
    """Return (subject, {predicate: [objects]}) for one Turtle block."""
    lines = block.split('\n')
    subject = lines[0].split('>', 1)[0].lstrip('<')
    props = defaultdict(list)
    for line in lines[1:]:
        if not line.startswith('\t') or line.startswith('\t\t'):
            continue  # skips the nested canonicalForm [ ... ] lines, the lemma comes from rdfs:label
        line = line.strip()
        if ' ' not in line or line.startswith(']'):
            continue
        predicate, rest = line.split(' ', 1)
        for literal, lang, uri, name in OBJECT_RE.findall(rest):
            if uri:
                props[predicate].append(uri)
            elif name:
                props[predicate].append(name)
            else:
                props[predicate].append((clean_text(literal), lang))
    return subject, props


def read_blocks(ttl_path):
    with open(ttl_path, 'r', encoding='utf-8') as f:
        block = []
        for line in f:
            line = line.rstrip('\n')
            if not line.strip():
                if block:
                    yield '\n'.join(block)
                    block = []
            elif not line.startswith('#') and not line.startswith('@prefix'):
                block.append(line)
        if block:
            yield '\n'.join(block)


def convert_to_json(raw_dir='data/raw/tatar', ttl_file='tatwordnet.ttl'):
    """
    Convert TatWordNet (Turtle / OntoLex) into the standard GWA LMF-style dict
    used across all converters in this project.

    Returns
    -------
    dict with keys: 'meta', 'synsets', 'lexical_entries'
    """
    synsets = {}                        # synset id -> synset dict
    entries = {}                        # entry uri -> (lemma, pos)
    sense_links = []                    # (entry uri, synset id)
    relations = defaultdict(list)       # synset id -> [(relType, target id)]

    for block in read_blocks(f'{raw_dir}/{ttl_file}'):
        subject, props = parse_block(block)

        if subject.startswith(BASE + 'synset/'):
            synset_id = local_id(subject, 'synset')
            ili = ''
            if props.get('wn:ili'):
                ili = props['wn:ili'][0].rsplit('/', 1)[-1]
            pos = POS_MAP.get(props.get('wn:partOfSpeech', ['u'])[0], 'u')
            synsets[synset_id] = {
                'id': synset_id,
                'ili': ili,
                'pos': pos,
                'definition': '',
                'examples': [],
                'semfield': '',
                'relations': []
            }

        elif subject.startswith(BASE + 'entry/'):
            labels = [text for text, lang in props.get('rdfs:label', []) if lang == 'tt']
            if not labels:
                continue
            pos = POS_MAP.get(props.get('wn:partOfSpeech', ['u'])[0], 'u')
            entries[subject] = (labels[0], pos)

        elif subject.startswith(BASE + 'sense/'):
            entry_uri = props.get('ontolex:isSenseOf', [None])[0]
            synset_uri = props.get('ontolex:reference', [None])[0]
            if entry_uri and synset_uri:
                sense_links.append((entry_uri, local_id(synset_uri, 'synset')))

        elif subject.startswith(BASE + 'relation/'):
            category = props.get('vartrans:category', [None])[0]
            source = props.get('vartrans:source', [None])[0]
            target = props.get('vartrans:target', [None])[0]
            if category and source and target:
                rel_type = category.split(':', 1)[1]
                relations[local_id(source, 'synset')].append((rel_type, local_id(target, 'synset')))

    # attach relations, only to synsets that exist (otherwise the XML has broken references)
    for synset_id, rels in relations.items():
        if synset_id not in synsets:
            continue
        seen = set()
        for rel_type, target in rels:
            if target in synsets and (rel_type, target) not in seen:
                seen.add((rel_type, target))
                synsets[synset_id]['relations'].append({'target': target, 'relType': rel_type})

    lemma_to_synsets = defaultdict(list)
    for entry_uri, synset_id in sense_links:
        if entry_uri not in entries or synset_id not in synsets:
            continue
        key = entries[entry_uri]
        if synset_id not in lemma_to_synsets[key]:
            lemma_to_synsets[key].append(synset_id)

    lexical_entries = [
        {'id': i, 'lemma': lemma, 'pos': pos, 'senses': synset_ids}
        for i, ((lemma, pos), synset_ids) in enumerate(lemma_to_synsets.items())
    ]

    return {
        'meta': {
            'id': 'tatwordnet-tt',
            'label': 'TatWordNet',
            'language': 'tt',
            'email': 'alik.kirillovich@gmail.com; iga.masniak@ens.psl.eu',
            'license': 'https://creativecommons.org/licenses/by-sa/4.0/',
            'version': '1.1',
            'dc:creator': 'Alexander Kirillovich, Marat Shaekhov, Alfiya Galieva, Olga Nevzorova, '
                          'Dmitry Ilvovsky, Natalia Loukachevitch',
            'dc:contributor': 'Iga Masniak',
            'dc:source': 'http://wordnet.tatar/',
            'dc:description': 'TatWordNet converted to GWA LMF format by Iga Masniak'
        },
        'synsets': list(synsets.values()),
        'lexical_entries': lexical_entries
    }


if __name__ == '__main__':
    result = convert_to_json()
    with open('data/jsons/TatarWordNet_standard.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=4, ensure_ascii=False)

    print('Done: TatarWordNet_standard.json')
    print(f"Synsets: {len(result['synsets'])}")
    print(f"Lexical entries: {len(result['lexical_entries'])}")