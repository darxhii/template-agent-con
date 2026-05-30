import json
from search_retail import search

queries = [
    "e-commerce impact on downtown retail vacancy rates",
    "national retail vacancy rate 2023 2024",
    "Chicago retail vacancy rate 2023 2024",
    "New York retail vacancy rate 2023 2024"
]

all_results = []
for q in queries:
    res = search(q)
    for r in res:
        r['query'] = q
        all_results.append(r)

with open('retail_results2.json', 'w') as f:
    json.dump(all_results, f, indent=2)
