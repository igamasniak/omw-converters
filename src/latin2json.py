import csv
import os
import json
from collections import defaultdict
from WordNetMapper import WordNetMapper

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def _load_ili_lookup(cili_path):
    pwn_2_ili = {}
    with open(cili_path, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            pwn_2_ili[row['origin'][8:16]] = row['ili_id']
    return pwn_2_ili


def split_gloss(text, lang):
    text = text.strip().strip('"')
    for sep in ['||', '; "', ': "', ';"', ':"']:
        if sep in text:
            parts = text.split(sep, 1)
            definition = parts[0].strip()
            example = parts[1].strip()
            example = example.replace('"; "', '; ')
            example = example.replace('\\"', '')
            example = example.replace('"', '')
            example = example.strip()
            return definition, example
    return text.strip(), ""


def split_examples(text):
    if not text:
        return []
    parts = text.split('||')
    return [p.strip() for p in parts if p.strip()]


def convert_to_json(raw_json_path='data/raw/latin/wordnet.json', cili_path='data/cili.tsv'):
    """
    Convert (non-revised) Latin WordNet raw JSON into the standard GWA
    LMF-style dict used across all converters in this project.

    Parameters
    ----------
    raw_json_path : str
        Path to the raw wordnet.json file
    cili_path : str
        Path to the cili.tsv ILI lookup file

    Returns
    -------
    dict with keys: 'meta', 'synsets', 'lexical_entries'
    """
    my_mapper = WordNetMapper()
    pwn_2_ili = _load_ili_lookup(cili_path)

    with open(raw_json_path, 'r', encoding='utf-8') as f:
        wordnet_data = json.load(f)

    synsets_by_lang = defaultdict(list)
    senses_by_lang = defaultdict(list)
    seen_synsets = defaultdict(set)

    for entry in wordnet_data:
        lemma = entry.get('lemma', '')
        pos = entry.get('pos', 'u')

        if not lemma:
            continue

        synsets_dict = entry.get('synsets', {})

        for synset_type in ['literal', 'metonymic', 'metaphoric']:
            synset_list = synsets_dict.get(synset_type, [])

            for synset in synset_list:
                offset = synset.get('offset', '')
                gloss = synset.get('gloss', '')
                semfield_list = synset.get('semfield', [])

                if not offset:
                    continue

                ili = ''
                if offset[0].isalpha():
                    ili = ''
                else:
                    try:
                        padded_offset = f"{int(offset):08d}"
                        pwn_offset, mapped_pos = my_mapper.map_offset_to_offset(padded_offset, "16", "30")
                        ili = pwn_2_ili.get(pwn_offset, '')
                    except Exception:
                        ili = ''

                if offset not in seen_synsets['Latin']:
                    seen_synsets['Latin'].add(offset)

                    definition, example = split_gloss(gloss, 'Latin')
                    examples = split_examples(example)

                    semfield = ''
                    if semfield_list:
                        semfield = '; '.join([sf.get('english', '') for sf in semfield_list])

                    synsets_by_lang['Latin'].append({
                        'id': offset,
                        'ili': ili,
                        'pos': pos,
                        'definition': definition,
                        'examples': examples,
                        'semfield': semfield,
                        'relations': []
                    })

                senses_by_lang['Latin'].append((offset, lemma))

    lang = 'Latin'
    lemma_to_synsets = defaultdict(list)

    for offset, lemma in senses_by_lang[lang]:
        if offset not in lemma_to_synsets[lemma]:
            lemma_to_synsets[lemma].append(offset)

    return {
        'meta': {
            'id': 'latin-la',
            'label': 'Latin WordNet',
            'language': 'la',
            'email': 'iga.masniak@ens.psl.eu',
            'license': '',
            'version': '',
            'dc:creator': 'William Michael Short',
            'dc:contributor': 'Iga Masniak',
            'dc:description': 'Latin WordNet converted to GWA LMF format by Iga Masniak'
        },
        'synsets': synsets_by_lang[lang],
        'lexical_entries': [
            {'id': i, 'lemma': l, 'senses': s} for i, (l, s) in enumerate(lemma_to_synsets.items())
        ]
    }


if __name__ == '__main__':
    result = convert_to_json()
    with open('data/jsons/LatinWordNet_standard.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=4, ensure_ascii=False)

    print('Done: LatinWordNet_standard.json')
    print(f"Synsets: {len(result['synsets'])}")
    print(f"Lexical entries: {len(result['lexical_entries'])}")