import os
import re
from collections import defaultdict

from src.common import build_output, make_synset, save_output

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RAW_PATH = 'data/raw/tatar/tatwordnet.ttl'
BASE = 'http://lod.wordnet.tatar/'

POS_MAP = {'wn:noun': 'n', 'wn:verb': 'v', 'wn:adjective': 'a'}

OBJECT_RE = re.compile(r'"((?:[^"\\]|\\.)*)"(?:@([\w-]+))?|<([^>]*)>|([A-Za-z]+:[\w-]+)')

META = {
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
}


def local_id(uri, kind):
    return uri[len(BASE + kind + '/'):]


def parse_block(block):
    lines = block.split('\n')
    subject = lines[0].split('>', 1)[0].lstrip('<')
    props = defaultdict(list)
    for line in lines[1:]:
        if not line.startswith('\t') or line.startswith('\t\t'):
            continue
        line = line.strip()
        if ' ' not in line or line.startswith(']'):
            continue
        predicate, rest = line.split(' ', 1)
        for literal, lang, uri, name in OBJECT_RE.findall(rest):
            props[predicate].append(uri or name or (literal.replace('\\"', '"').replace('\\\\', '\\'), lang))
    return subject, props


def read_blocks(path):
    with open(path, encoding='utf-8') as f:
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


def read_source(path):
    synsets, entries, sense_links, relations = {}, {}, [], []
    for block in read_blocks(path):
        subject, props = parse_block(block)
        first = lambda key: (props.get(key) or [None])[0]

        if subject.startswith(BASE + 'synset/'):
            ili = first('wn:ili')
            synsets[local_id(subject, 'synset')] = (POS_MAP.get(first('wn:partOfSpeech'), 'u'),
                                                    ili.rsplit('/', 1)[-1] if ili else '')
        elif subject.startswith(BASE + 'entry/'):
            labels = [text for text, lang in props.get('rdfs:label', []) if lang == 'tt']
            if labels:
                entries[subject] = (labels[0], POS_MAP.get(first('wn:partOfSpeech'), 'u'))
        elif subject.startswith(BASE + 'sense/'):
            if first('ontolex:isSenseOf') and first('ontolex:reference'):
                sense_links.append((first('ontolex:isSenseOf'), local_id(first('ontolex:reference'), 'synset')))
        elif subject.startswith(BASE + 'relation/'):
            if first('vartrans:category') and first('vartrans:source') and first('vartrans:target'):
                relations.append((local_id(first('vartrans:source'), 'synset'),
                                  first('vartrans:category').split(':', 1)[1],
                                  local_id(first('vartrans:target'), 'synset')))
    return synsets, entries, sense_links, relations


def convert_to_json(raw_path=RAW_PATH):
    raw_synsets, entries, sense_links, raw_relations = read_source(raw_path)

    synsets = {synset_id: make_synset(synset_id, pos, ili) for synset_id, (pos, ili) in raw_synsets.items()}
    for source, rel_type, target in dict.fromkeys(raw_relations):
        if source in synsets and target in synsets:
            synsets[source]['relations'].append({'target': target, 'relType': rel_type})

    senses = [(*entries[entry], synset_id) for entry, synset_id in sense_links if entry in entries]
    return build_output(META, synsets, senses)


if __name__ == '__main__':
    save_output(convert_to_json(), 'TatarWordNet')