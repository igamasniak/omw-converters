# GWA LMF Conversion Pipeline

This project's aim is to convert WordNets in various source formats into
standard Global WordNet Association Lexical Markup Framework (WN-LMF) xml
format.

## INSTRUCTIONS

## Run

```bash
python3 src/run.py
```

Run this single command from the project root. It performs the full
pipeline end to end:

### 1. Convert each source WordNet to standard json

Uses the matching `src/*2json.py` script for that language, listed in
`CONVERTERS` in `run.py`. Each script links its synsets to the CILI
(Collaborative Interlingual Index), the GWA's shared registry of
language neutral concept IDs, `cili.tsv`, so
equivalent concepts can be matched across languages (`ili` value). Several of these
scripts depend on WordNetMapper (see below) already being installed.

### 2. Convert each standard JSON file to WN-LMF xml

Carries over the `ili` value into each `Synset` element.

### 3. Validate every generated xml file

Checks against `WN-LMF-1.4.dtd`, the schema defining which elements a valid WN-LMF file may contain.

### 4. Compress each validated file individually with xz

Produces `data/xmls/<Language>WordNet.xml.xz`.

## WordNetMapper

Source: https://github.com/cltl/WordNetMapper

Not installed automatically. The language specific json converters that
need PWN version mapping import it directly, so it needs to already be
imported before running `python3 src/run.py`. Set up with:

```bash
git clone https://github.com/cltl/WordNetMapper.git
cp WordNetMapper/wordnet_mapper.py src/
```

## Adding a new WordNet

1. A `<language>2json.py` script in `src/` reads the raw source and
   produces the standard JSON schema (`meta`, `synsets`,
   `lexical_entries`, see any existing `*2json.py` for the format).
2. Add it to the `CONVERTERS` list in `run.py`.
3. `python3 src/run.py`. The new language then goes through json, xml,
   validation, and compression along with the rest.
