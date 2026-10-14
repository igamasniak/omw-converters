import os

from lxml import etree

from src.common import build_output, make_synset, save_output

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RAW_PATH = 'data/raw/finnish/finnwordnet-2.0-lmf.xml'

META = {
    'id': 'finnish-fi',
    'label': 'FinnWordNet',
    'language': 'fi',
    'email': 'krister.linden@helsinki.fi',
    'license': 'CC BY 3.0',
    'version': '2.0.1',
    'dc:creator': 'Krister Lindén & Jyrki Niemi',
    'dc:contributor': 'Iga Masniak',
    'dc:description': 'Finnish WordNet converted to GWA LMF format by Iga Masniak'
}


def read_source(path):
    return etree.parse(path).find('.//Lexicon')


def convert_to_json(raw_path=RAW_PATH):
    lexicon = read_source(raw_path)
    synsets, senses = {}, []

    for s in lexicon.findall('Synset'):
        synsets[s.get('id')] = make_synset(
            s.get('id'),
            s.get('partOfSpeech', 'u'),
            s.get('ili', ''),
            s.findtext('Definition') or '',
            [ex.text for ex in s.findall('Example')],
            relations=[{'target': r.get('target'), 'relType': r.get('relType')} for r in s.findall('SynsetRelation')]
        )

    for entry in lexicon.findall('LexicalEntry'):
        lemma = entry.find('Lemma')
        pos = lemma.get('partOfSpeech', 'u')
        senses += [(lemma.get('writtenForm'), pos, sense.get('synset')) for sense in entry.findall('Sense')]

    return build_output(META, synsets, senses)


if __name__ == '__main__':
    save_output(convert_to_json(), 'FinnishWordNet')