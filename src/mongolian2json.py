import os
import re
from collections import defaultdict

from src.common import IliResolver, build_output, clean_text, make_synset, save_output

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RAW_PATH = 'data/raw/mongolian/wn-data-mon.tsv'

META = {
    'id': 'monwn-mn',
    'label': 'Mongolian Wordnet',
    'language': 'mn',
    'email': 'iga.masniak@ens.psl.eu',
    'license': 'https://creativecommons.org/licenses/by/4.0/',
    'version': '1.0',
    'dc:creator': 'Khuyagbaatar Batsuren, Amarsanaa Ganbold, Altangerel Chagnaa, Fausto Giunchiglia',
    'dc:contributor': 'Iga Masniak',
    'dc:source': 'https://github.com/kbatsuren/monwn',
    'dc:description': 'Mongolian Wordnet (MonWN) converted to GWA LMF format by Iga Masniak'
}


def split_gloss(text):
    match = re.search(r'\s*;\s*[“"]', text)
    if not match:
        return text, []
    return text[:match.start()], re.findall(r'[“"]([^”"]+)[”"]', text[match.start():])


def read_source(path):
    rows = defaultdict(lambda: {'lemmas': [], 'definition': '', 'examples': []})
    with open(path, encoding='utf-8') as f:
        for line in f:
            cols = line.rstrip('\n').split('\t')
            if line.startswith('#') or len(cols) != 3 or not re.fullmatch(r'\d{8}-[nvasr]', cols[0]):
                continue
            synset_id, field, value = cols[0], cols[1], clean_text(cols[2])
            if field == 'mon:lemma':
                rows[synset_id]['lemmas'].append(value)
            elif field.startswith('mon:def'):
                definition, examples = split_gloss(value)
                rows[synset_id]['definition'] = definition
                rows[synset_id]['examples'] += examples
            elif field.startswith('mon:exe'):
                rows[synset_id]['examples'].append(value)
    return rows


def convert_to_json(raw_path=RAW_PATH, cili_path='data/cili.tsv'):
    ili = IliResolver(cili_path)
    synsets, senses = {}, []

    for synset_id, row in read_source(raw_path).items():
        offset, pos = synset_id.split('-')
        pos = ili.pwn_pos(offset, pos)
        synsets[synset_id] = make_synset(synset_id, pos, ili.get(offset, pos, '30'),
                                         row['definition'], row['examples'])
        senses += [(lemma, pos, synset_id) for lemma in row['lemmas']]

    return build_output(META, synsets, senses)


if __name__ == '__main__':
    save_output(convert_to_json(), 'MongolianWordNet')