import json
import os

from src.common import IliResolver, build_output, make_synset, save_output

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RAW_PATH = 'data/raw/sanskrit/wordnet.json'

SENSE_TYPES = ['literal', 'metonymic', 'metaphoric']

POS_MAP = {'n': 'n', 'v': 'v', 'a': 'a', 'r': 'r', '-': 'u'}
SYNSET_POS = {'n', 'v', 'a', 'r'}

META = {
    'id': 'sanskrit-sa',
    'label': 'Sanskrit WordNet',
    'language': 'sa',
    'email': 'iga.masniak@ens.psl.eu',
    'license': '',
    'version': '',
    'dc:creator': 'William Michael Short',
    'dc:contributor': 'Iga Masniak',
    'dc:description': 'Sanskrit WordNet converted to GWA LMF format by Iga Masniak'
}


def split_gloss(text):
    text = text.strip().strip('"')
    for sep in ['||', '; "', ': "', ';"', ':"']:
        if sep in text:
            definition, example = text.split(sep, 1)
            return definition, example.replace('\\"', '').replace('"', '').split('||')
    return text, []


def read_source(path):
    with open(path, encoding='utf-8') as f:
        return json.loads(f.read().replace('\x12', 'Ṛ'))


def convert_to_json(raw_path=RAW_PATH, cili_path='data/cili.tsv'):
    ili = IliResolver(cili_path)
    synsets, senses = {}, []

    for entry in read_source(raw_path):
        lemma = entry.get('lemma')
        lemma_pos = POS_MAP.get(entry.get('pos'), 'x')

        for synset_type in SENSE_TYPES:
            for synset in (entry.get('synsets') or {}).get(synset_type) or []:
                offset = (synset.get('offset') or '').strip()
                synset_pos = synset.get('pos')
                if not offset or synset_pos not in SYNSET_POS:
                    continue

                synset_id = f'{offset}-{synset_pos}'
                if synset_id not in synsets:
                    definition, examples = split_gloss(synset.get('gloss') or '')
                    semfield = '; '.join(s.get('english', '') for s in synset.get('semfield') or [] if s.get('english'))
                    synsets[synset_id] = make_synset(synset_id, synset_pos, ili.get(offset, synset_pos, '16'),
                                                     definition, examples, semfield)
                senses.append((lemma, lemma_pos, synset_id))

    return build_output(META, synsets, senses)


if __name__ == '__main__':
    save_output(convert_to_json(), 'SanskritWordNet')