import csv
import os
import re

from src.common import IliResolver, build_output, clean_text, make_synset, save_output

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RAW_PATH = 'data/raw/filipino/filwordnet.csv'

POS_FROM_PREFIX = {'1': 'n', '2': 'v', '3': 'a', '4': 'r'}

META = {
    'id': 'filwordnet-fil',
    'label': 'Filipino WordNet',
    'language': 'fil',
    'email': 'iga.masniak@ens.psl.eu',
    'license': '',
    'version': '2026-10-12',
    'dc:creator': 'Allan Borra, Adam Pease, Rachel Edita Roxas, Shirley Dita',
    'dc:contributor': 'Iga Masniak',
    'dc:source': 'https://github.com/danjohnvelasco/Filipino-WordNet',
    'dc:description': 'Filipino WordNet converted to GWA LMF format by Iga Masniak'
}


def split_lemmas(lemma):
    lemma = lemma.replace('\\', '').replace('_', ' ').rstrip('?')
    return [clean_text(p) for p in lemma.split('/') if clean_text(p)]


def clean_sumo(sumo):
    sumo = re.sub(r'[\[\]@=+:]', '', sumo or '').strip()
    return '' if sumo == 'None' else sumo


def read_source(path):
    with open(path, encoding='utf-8') as f:
        return [row for row in csv.DictReader(f) if re.fullmatch(r'[1-4]\d{8}', row['synsetid'].strip())]


def convert_to_json(raw_path=RAW_PATH, cili_path='data/cili.tsv'):
    ili = IliResolver(cili_path)
    synsets, lemmas = {}, []

    for row in read_source(raw_path):
        synset_id = row['synsetid'].strip()
        offset, pos = synset_id[1:], POS_FROM_PREFIX[synset_id[0]]

        if synset_id not in synsets:
            synsets[synset_id] = make_synset(synset_id, pos, ili.get(offset, pos, '30'),
                                             row['definition'], semfield=clean_sumo(row['sumo']))
        if pos == 'a' and row['pos'].strip() == 's':
            synsets[synset_id]['pos'] = 's'

        lemmas += [(lemma, synset_id) for lemma in split_lemmas(row['lemma'])]

    senses = [(lemma, synsets[synset_id]['pos'], synset_id) for lemma, synset_id in lemmas]
    return build_output(META, synsets, senses)


if __name__ == '__main__':
    save_output(convert_to_json(), 'FilipinoWordNet')