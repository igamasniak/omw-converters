import csv
import os
import re

from src.common import IliResolver, build_output, make_synset, save_output

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RAW_PATH = 'data/raw/latin_revised/LiLa_LatinWordnet.csv'

META = {
    'id': 'latin-revised-csv-la',
    'label': 'Latin WordNet (LiLa CSV)',
    'language': 'la',
    'email': 'iga.masniak@ens.psl.eu',
    'license': 'https://creativecommons.org/licenses/by-sa/4.0/',
    'version': '',
    'dc:creator': 'Eleonora Litta, Greta Franzini, Giulia Pedonese, Marco Passarotti',
    'dc:contributor': 'Iga Masniak',
    'dc:description': 'LiLa Latin WordNet CSV converted to GWA LMF format by Iga Masniak'
}


def read_source(path):
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def convert_to_json(raw_path=RAW_PATH, cili_path='data/cili.tsv'):
    ili = IliResolver(cili_path)
    synsets, senses = {}, []

    for row in read_source(raw_path):
        match = re.search(r'(\d{8}-[nvasr])', row['id_synset'] or '')
        lemma = (row['lemma'] or '').strip()
        if not match or not lemma:
            continue

        synset_id = match.group(1)
        offset, pos = synset_id.split('-')
        if synset_id not in synsets:
            synsets[synset_id] = make_synset(synset_id, pos, ili.get(offset, pos, '30'), row['definition'] or '')
        senses.append((lemma, pos, synset_id))

    return build_output(META, synsets, senses)


if __name__ == '__main__':
    save_output(convert_to_json(), 'LatinWordNet_revised_csv')