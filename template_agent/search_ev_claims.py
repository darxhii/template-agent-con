import json
from ddgs import DDGS

queries = [
    "Biden administration $1.7 billion grants convert at-risk auto plants EV production",
    "European Commission €1 billion call EV battery cell manufacturing Innovation Fund 2024",
    "EU definitive countervailing duties 35.3% battery electric vehicles China October 2024",
    "China spent at least $230 billion on EV sector since 2009",
    "China new energy vehicle sales nearly 13 million units in 2024",
    "Chinese government pull plug on broad EV subsidies, excluding from upcoming five-year plans",
    "India PLI scheme attracted over ₹25,000 crore capital commitments by December 2024",
    "Brazil approved MOVER program in 2024 to incentivize sustainable vehicle technologies"
]

results = []
for q in queries:
    try:
        res = list(DDGS().text(q, max_results=5))
        for r in res:
            results.append({
                "query": q,
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "content": r.get("body", "")
            })
    except Exception as e:
        print(f"Error on {q}: {e}")

with open("search_results_2.json", "w") as f:
    json.dump(results, f, indent=2)
print(f"Saved {len(results)} results.")
