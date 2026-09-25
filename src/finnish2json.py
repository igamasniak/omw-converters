
import json
import os
from lxml import etree

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_XML_PATH = os.path.join(_ROOT, 'data', 'raw', 'finnish', 'finnwordnet-2.0-lmf.xml')
_DEFAULT_OUTPUT_PATH = os.path.join(_ROOT, 'data', 'jsons', 'FinnishWordNet_standard.json')


def convert_to_json(xml_path=_DEFAULT_XML_PATH):

    tree = etree.parse(xml_path)
    lexicon = tree.find('.//Lexicon')

    synsets = []
    for s in lexicon.findall('Synset'):
        defn = s.find('Definition')
        examples = [ex.text for ex in s.findall('Example') if ex.text]
        relations = [
            {'target': rel.get('target'), 'relType': rel.get('relType')}
            for rel in s.findall('SynsetRelation')
        ]

        synsets.append({
            'id': s.get('id'),
            'ili': s.get('ili', ''),
            'pos': s.get('partOfSpeech', 'u'),
            'definition': defn.text if defn is not None and defn.text else '',
            'examples': examples,
            'semfield': '',
            'relations': relations,
        })

    lexical_entries = []
    for i, entry in enumerate(lexicon.findall('LexicalEntry')):
        lemma = entry.find('Lemma')
        senses = [sense.get('synset') for sense in entry.findall('Sense')]
        lexical_entries.append({
            'id': i,
            'lemma': lemma.get('writtenForm'),
            'pos': lemma.get('partOfSpeech', 'n'),
            'senses': senses,
        })

    output = {
        'meta': {
            'id': 'finnish-fi',
            'label': 'FinnWordNet',
            'language': 'fi',
            'email': 'krister.linden@helsinki.fi',
            'license': 'CC BY 3.0',
            'version': '2.0.1',
            'dc:creator': 'Krister Lindén & Jyrki Niemi',
            'dc:contributor': 'Iga Masniak',
            'dc:description': 'Finnish WordNet converted to GWA LMF format by Iga Masniak',
        },
        'synsets': synsets,
        'lexical_entries': lexical_entries,
    }
    return output


if __name__ == '__main__':
    data = convert_to_json()

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
