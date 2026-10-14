import csv
import os
import re
from functools import lru_cache

from src.common import IliResolver, build_output, make_synset, save_output

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RAW_PATH = 'data/new_indo_wordnet.tsv'

LANG_CODES = {
    'kashmiri': 'ks', 'konkani': 'kok', 'assamese': 'as',
    'nepali': 'ne', 'sanskrit': 'sa', 'marathi': 'mr',
    'kannada': 'kn', 'oriya': 'or', 'punjabi': 'pa',
    'urdu': 'ur', 'gujarati': 'gu', 'bodo': 'brx',
    'malayalam': 'ml', 'english': 'en', 'manipuri': 'mni',
    'hindi': 'hi', 'telugu': 'te', 'tamil': 'ta'
}

SUPPORTED_LANGUAGES = list(LANG_CODES)

POS_MAP = {'NOUN': 'n', 'VERB': 'v', 'ADJECTIVE': 'a', 'ADVERB': 'r'}


def meta(lang):
    return {
        'id': f'indowordnet-{LANG_CODES[lang]}',
        'label': f'IndoWordnet {lang.capitalize()}',
        'language': LANG_CODES[lang],
        'email': 'pb@cse.iitb.ac.in; dipteshkanojia@gmail.com; iga.masniak@ens.psl.eu',
        'license': 'https://creativecommons.org/licenses/by-nc-sa/4.0/',
        'version': '0.5',
        'dc:creator': 'Pushpak Bhattacharyya; Diptesh Kanojia',
        'dc:contributor': 'Iga Masniak',
        'dc:description': (
            'IndoWordNet converted to GWA LMF format by Iga Masniak (iga.masniak@ens.psl.eu). '
            'Original wordnet created by Pushpak Bhattacharyya (pb@cse.iitb.ac.in). '
            'Data maintained by Diptesh Kanojia (dipteshkanojia@gmail.com).'
        )
    }


def split_gloss(text):
    text = (text or '').strip().strip('"')
    for sep in ['||', '; "', ': "', ';"', ':"']:
        if sep in text:
            definition, example = text.split(sep, 1)
            example = example.replace('\\"', '').replace('"', '')
            return definition, [p.strip('।') for p in re.split(r'[।]?\s*[/;]\s*', example)]
    return text, []


def split_lemmas(text, lang):
    lemmas = []
    for lemma in (text or '').split(','):
        parts = [lemma]
        if lang in ('kashmiri', 'urdu'):
            parts = [p for p in re.split(r'[،۔]', lemma) if p.strip()] or [lemma]
        lemmas += [p.replace('_', ' ').strip() for p in parts if p.strip()]
    return lemmas


@lru_cache(maxsize=None)
def ili_resolver(cili_path):
    return IliResolver(cili_path)


@lru_cache(maxsize=None)
def read_source(path):
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f, delimiter='\t'))


def convert_to_json(lang, raw_path=RAW_PATH, cili_path='data/cili.tsv'):
    ili = ili_resolver(cili_path)
    synsets, senses = {}, []
    synset_column = 'english_synset_words' if lang == 'english' else f'{lang}_synset'

    for row in read_source(raw_path):
        synset_id = row['hindi_id']
        pos = POS_MAP.get((row.get('hindi_category_x') or '').strip().upper())
        lemmas = split_lemmas(row.get(synset_column), lang)
        if not pos or not lemmas:
            continue

        synset_ili = ili.get(row['english_id'], pos, '21') if row.get('type_link') == 'Direct' else ''
        definition, examples = split_gloss(row.get(f'{lang}_gloss'))
        synsets[synset_id] = make_synset(synset_id, pos, synset_ili, definition, examples)
        senses += [(lemma, pos, synset_id) for lemma in lemmas]

    return build_output(meta(lang), synsets, senses)


if __name__ == '__main__':
    for language in SUPPORTED_LANGUAGES:
        save_output(convert_to_json(language), f'IndoWordNet_{language}')