import csv
import os
import json
import re
from collections import defaultdict
from WordNetMapper import WordNetMapper

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def clean_text(text):
    if not text:
        return text
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)


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


def _load_ili_lookup(cili_path):
    pwn_2_ili = {}
    with open(cili_path, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            pwn_2_ili[row['origin'][8:16]] = row['ili_id']
    return pwn_2_ili


def _load_wordnet_data(wordnet_json_path):
    with open(wordnet_json_path, 'r', encoding='utf-8') as f:
        raw = f.read()
    raw = raw.replace('\x12', 'Ṛ')
    return json.loads(raw)


def convert_to_json(raw_dir='data/raw/sanskrit', cili_path='data/cili.tsv'):
    """
    Convert Sanskrit WordNet raw JSON into the standard GWA LMF-style dict
    used across all converters in this project.

    Parameters
    ----------
    raw_dir : str
        Directory containing wordnet.json
    cili_path : str
        Path to the cili.tsv ILI lookup file

    Returns
    -------
    dict with keys: 'meta', 'synsets', 'lexical_entries'
    """
    my_mapper = WordNetMapper()
    pwn_2_ili = _load_ili_lookup(cili_path)
    wordnet_data = _load_wordnet_data(f'{raw_dir}/wordnet.json')

    synsets_by_lang = defaultdict(list)
    senses_by_lang = defaultdict(list)
    seen_synsets = defaultdict(set)

    pos_map = {
        '-': 'u',  # unknown
    }

    for entry in wordnet_data:
        lemma = entry.get('lemma', '')
        raw_pos = entry.get('pos', 'u')
        pos = pos_map.get(raw_pos, raw_pos)

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

                if offset not in seen_synsets['Sanskrit']:
                    seen_synsets['Sanskrit'].add(offset)

                    definition, example = split_gloss(gloss, 'Sanskrit')
                    examples = split_examples(example)

                    semfield = ''
                    if semfield_list:
                        semfield = '; '.join([sf.get('english', '') for sf in semfield_list])

                    synsets_by_lang['Sanskrit'].append({
                        'id': offset,
                        'ili': ili,
                        'pos': pos,
                        'definition': clean_text(definition),
                        'examples': [clean_text(ex) for ex in examples],
                        'semfield': clean_text(semfield),
                        'relations': []
                    })

                senses_by_lang['Sanskrit'].append((offset, clean_text(lemma), pos))

    lang = 'Sanskrit'
    lemma_to_synsets = defaultdict(list)
    lemma_pos = {}

    for offset, lemma, pos in senses_by_lang[lang]:
        key = (lemma, pos)
        if offset not in lemma_to_synsets[key]:
            lemma_to_synsets[key].append(offset)
        lemma_pos[key] = pos

    lexical_entries = [
        {'id': i, 'lemma': lemma, 'pos': pos, 'senses': senses}
        for i, ((lemma, pos), senses) in enumerate(lemma_to_synsets.items())
    ]

    return {
        'meta': {
            'id': 'sanskrit-sa',
            'label': 'Sanskrit WordNet',
            'language': 'sa',
            'email': 'iga.masniak@ens.psl.eu',
            'license': 'https://creativecommons.org/licenses/by-nc-sa/4.0/',
            'version': '',
            'dc:creator': 'William Michael Short',
            'dc:contributor': 'Iga Masniak',
            'dc:description': 'Sanskrit WordNet converted to GWA LMF format by Iga Masniak'
        },
        'synsets': synsets_by_lang[lang],
        'lexical_entries': lexical_entries
    }


if __name__ == '__main__':
    result = convert_to_json()
    with open('data/jsons/SanskritWordNet_standard.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=4, ensure_ascii=False)

    print('Done: SanskritWordNet_standard.json')
    print(f"Synsets: {len(result['synsets'])}")
    print(f"Lexical entries: {len(result['lexical_entries'])}")