import json
from ddgs import DDGS

queries = [
    "US Inflation Reduction Act EV manufacturing subsidies 2024",
    "European Union EV manufacturing subsidies policies 2024",
    "China electric vehicle manufacturing incentives government support 2024",
    "global EV manufacturing incentives comparison 2024",
    "automakers EV manufacturing subsidies impact 2024"
]

results = []
for q in queries:
    try:
        res = list(DDGS().text(q, max_results=8))
        for r in res:
            results.append({
                "query": q,
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "content": r.get("body", "")
            })
    except Exception as e:
        print(f"Error on {q}: {e}")

with open("search_results.json", "w") as f:
    json.dump(results, f, indent=2)
print(f"Saved {len(results)} results.")
