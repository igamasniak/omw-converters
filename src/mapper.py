
my_mapper = WordNetMapper()
pwn_2_ili={}
with open('data/cili.tsv') as tsvfile:
    reader = csv.DictReader(tsvfile, delimiter='\t')
    for row in reader:
        ili=row["ili_id"]
        pwn=row['origin'][8:16]
        assert pwn not in ili
        pwn_2_ili[pwn]=ili

def test_mapping(english_index):
    for wordnet_version in ["16","17","171","20","21","30"]:
        try:
            pwn_offset, pos = my_mapper.map_offset_to_offset(english_index, wordnet_version, "30")
        except:
            continue
        ili_id = pwn_2_ili[pwn_offset]
        print(f"mapping found for wordnet version {wordnet_version}: {ili_id}")

def convert_to_ili(english_index, english_version):
    english_index = f"{english_index:08d}"
    pwn_offset, pos = my_mapper.map_offset_to_offset(english_index, english_version, "30")
    return pwn_2_ili[pwn_offset]

print(convert_to_ili(975187, "21"))

test_mapping("")

