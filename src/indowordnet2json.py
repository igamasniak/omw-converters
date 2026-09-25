import csv
import json
import os
import re
from collections import defaultdict
from functools import lru_cache

from WordNetMapper import WordNetMapper

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_TSV_PATH = os.path.join(_ROOT, 'data', 'new_indo_wordnet.tsv')
_DEFAULT_CILI_PATH = os.path.join(_ROOT, 'data', 'cili.tsv')
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Full language name (as used in the raw TSV column prefixes) -> ISO 639-3 code
LANG_CODES = {
    'kashmiri': 'ks', 'konkani': 'kok', 'assamese': 'as',
    'nepali': 'ne', 'sanskrit': 'sa', 'marathi': 'mr',
    'kannada': 'kn', 'oriya': 'or', 'punjabi': 'pa',
    'urdu': 'ur', 'gujarati': 'gu', 'bodo': 'brx',
    'malayalam': 'ml', 'english': 'en', 'manipuri': 'mni',
    'hindi': 'hi', 'telugu': 'te', 'tamil': 'ta'
}

SUPPORTED_LANGUAGES = list(LANG_CODES)


def _load_ili_lookup(cili_path):
    pwn_2_ili = {}
    with open(cili_path, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            pwn_2_ili[row['origin'][8:16]] = row['ili_id']
    return pwn_2_ili


def split_gloss(text):
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
    parts = re.split(r'[।]?\s*[/;]\s*', text)
    return [p.strip().strip('।').strip() for p in parts if p.strip().strip('।').strip()]


def split_lemma(lemma, lang):
    if lang in ['kashmiri', 'urdu']:
        parts = [p.strip() for p in lemma.split('،') if p.strip()]
        if len(parts) > 1:
            return parts
        # Kashmiri full stop as separator
        parts = [p.strip() for p in lemma.split('۔') if p.strip()]
        if len(parts) > 1:
            return parts
    return [lemma]


@lru_cache(maxsize=None)
def _build_all_language_data(tsv_path, cili_path):
    my_mapper = WordNetMapper()
    pwn_2_ili = _load_ili_lookup(cili_path)

    synsets_by_lang = defaultdict(list)
    senses_by_lang = defaultdict(list)
    seen_synsets = defaultdict(set)

    with open(tsv_path, encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            hindi_id = row['hindi_id']
            english_id = f"{int(row['english_id']):08d}"
            try:
                pwn_offset, pos = my_mapper.map_offset_to_offset(english_id, "21", "30")
                ili = pwn_2_ili[pwn_offset]
            except Exception:
                continue

            for k in [k for k in row if k.endswith('gloss')]:
                lang = k.split('_')[0]
                if hindi_id not in seen_synsets[lang]:
                    seen_synsets[lang].add(hindi_id)
                    definition, example = split_gloss(row[k])
                    synsets_by_lang[lang].append({
                        'id': hindi_id,
                        'ili': ili,
                        'pos': pos,
                        'definition': definition,
                        'examples': split_examples(example),
                        'semfield': '',
                        'relations': []
                    })

            for k in [k for k in row if 'synset' in k]:
                lang = k.split('_')[0]
                for lemma in row[k].split(','):
                    lemma = lemma.strip()
                    for split_lemma_part in split_lemma(lemma, lang):
                        senses_by_lang[lang].append((hindi_id, split_lemma_part))

    return synsets_by_lang, senses_by_lang


def convert_to_json(lang, tsv_path=_DEFAULT_TSV_PATH, cili_path=_DEFAULT_CILI_PATH):

    if lang not in LANG_CODES:
        raise ValueError(
            f"Unknown IndoWordNet language '{lang}'. "
            f"Supported languages: {sorted(LANG_CODES)}"
        )

    synsets_by_lang, senses_by_lang = _build_all_language_data(tsv_path, cili_path)
    lang_code = LANG_CODES[lang]

    lemma_to_synsets = defaultdict(list)
    for hindi_id, lemma in senses_by_lang.get(lang, []):
        if hindi_id not in lemma_to_synsets[lemma]:
            lemma_to_synsets[lemma].append(hindi_id)

    return {
        'meta': {
            'id': f'indowordnet-{lang_code}',
            'label': f'IndoWordnet {lang.capitalize()}',
            'language': lang_code,
            'email': 'pb@cse.iitb.ac.in; dipteshkanojia@gmail.com; iga.masniak@ens.psl.eu',
            'license': 'https://creativecommons.org/licenses/by-nc-sa/4.0/',
            'version': '1.0',
            'dc:creator': 'Pushpak Bhattacharyya; Diptesh Kanojia',
            'dc:contributor': 'Iga Masniak',
            'dc:description': (
                'IndoWordNet converted to GWA LMF format by Iga Masniak (iga.masniak@ens.psl.eu). '
                'Original wordnet created by Pushpak Bhattacharyya (pb@cse.iitb.ac.in). '
                'Data maintained by Diptesh Kanojia (dipteshkanojia@gmail.com).'
            )
        },
        'synsets': synsets_by_lang.get(lang, []),
        'lexical_entries': [
            {'id': i, 'lemma': l, 'senses': s} for i, (l, s) in enumerate(lemma_to_synsets.items())
        ]
    }


if __name__ == '__main__':
    for language in SUPPORTED_LANGUAGES:
        result = convert_to_json(language)
        with open(f'data/jsons/IndoWordNet_{language}.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=4, ensure_ascii=False)
        print(f"Done: IndoWordNet_{language}.json "
              f"({len(result['synsets'])} synsets, {len(result['lexical_entries'])} lexical entries)")
