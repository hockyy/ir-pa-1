from bsbi import BSBIIndex
from compression import VBEPostings, StandardPostings, EliasGammaPostings

# sebelumnya sudah dilakukan indexing
# BSBIIndex hanya sebagai abstraksi untuk index tersebut
BSBI_instance = BSBIIndex(data_dir = 'collection',
                          # postings_encoding = VBEPostings,
                          # postings_encoding = StandardPostings,
                          postings_encoding = EliasGammaPostings,
                          output_dir = 'index')
BSBI_instance.load()

# queries = ["olahraga", "tumor", "hidup sehat"]
queries = ["olahraga jantung teratur sehat hidup"]
for query in queries:
    print("Query  : ", query)
    print("Results:")
    for doc in sorted(BSBI_instance.retrieve(query)):
        print(doc)
    print()