import os
import csv
import json
from collections import defaultdict
import polib

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def _load_ili_lookup(cili_path):
    pwn_2_ili = {}
    with open(cili_path, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            pwn_2_ili[row['origin'][8:16]] = row['ili_id']
    return pwn_2_ili


def convert_to_json(po_path='data/raw/irish/ga-data.po', cili_path='data/cili.tsv'):
    """
    Convert Irish WordNet raw .po file into the standard GWA LMF-style
    dict used across all converters in this project.

    Parameters
    ----------
    po_path : str
        Path to the ga-data.po file
    cili_path : str
        Path to the cili.tsv ILI lookup file

    Returns
    -------
    dict with keys: 'meta', 'synsets', 'lexical_entries'
    """
    pwn_2_ili = _load_ili_lookup(cili_path)
    po = polib.pofile(po_path)

    synsets = {}
    senses = []

    for entry in po:
        offset_pos = entry.msgctxt
        if not offset_pos or '-' not in offset_pos:
            continue

        offset, pos = offset_pos.rsplit('-', 1)
        definition = entry.msgid.strip()

        # extracting Irish lemmas
        irish_lemmas = []
        if entry.tcomment:
            lines = entry.tcomment.split('\n')
            irish_line = lines[0].strip()
            irish_lemmas = [l.strip() for l in irish_line.split(',') if l.strip()]

        # ILI lookup
        ili = pwn_2_ili.get(offset, '')

        # storing synset
        if offset not in synsets:
            synsets[offset] = {
                'id': offset,
                'ili': ili,
                'pos': pos,
                'definition': definition,
                'examples': [],
                'semfield': '',
                'relations': []
            }

        # storing senses
        for lemma in irish_lemmas:
            if lemma:
                senses.append((offset, lemma))

    # NOTE: polib appears to swallow the tcomment of the very first .po entry
    # (likely mistaken for header metadata). This hardcodes the known-correct
    # lemmas for that entry (synset 00001740) as a workaround. If ga-data.po
    # is ever regenerated/updated, this list should be re-verified against
    # the source rather than assumed to still be correct.
    if '00001740' in synsets and '00001740' not in [s[0] for s in senses[:20]]:
        first_lemmas = ['in ann', 'maith', 'ábalta', 'cumasach', 'i gcumas', 'inniúil']
        for lemma in first_lemmas:
            senses.append(('00001740', lemma))

    # building lexical entries
    lemma_to_synsets = defaultdict(list)
    for offset, lemma in senses:
        if offset not in lemma_to_synsets[lemma]:
            lemma_to_synsets[lemma].append(offset)

    return {
        'meta': {
            'id': 'irish-ga',
            'label': 'Irish WordNet',
            'language': 'ga',
            'email': 'kscanne@gmail.com',
            'license': 'https://creativecommons.org/licenses/by-nc-sa/4.0/',
            'version': '1.0',
            'dc:creator': 'Kevin P. Scannell',
            'dc:contributor': 'Iga Masniak (iga.masniak@ens.psl.eu)',
            'dc:description': 'Irish WordNet converted to GWA LMF format by Iga Masniak'
        },
        'synsets': list(synsets.values()),
        'lexical_entries': [
            {'id': i, 'lemma': l, 'senses': s} for i, (l, s) in enumerate(lemma_to_synsets.items())
        ]
    }


if __name__ == '__main__':
    result = convert_to_json()
    with open('data/jsons/IrishWordNet_standard.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=4, ensure_ascii=False)

    print('Done: IrishWordNet_standard.json')
    print(f"Synsets: {len(result['synsets'])}")
    print(f"Lexical entries: {len(result['lexical_entries'])}")
