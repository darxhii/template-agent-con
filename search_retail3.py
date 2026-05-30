import urllib.request
import urllib.parse
import re
import json

def search(query):
    url = 'https://html.duckduckgo.com/html/?q=' + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    try:
        html = urllib.request.urlopen(req).read().decode('utf-8')
        snippets = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', html, re.IGNORECASE | re.DOTALL)
        urls = re.findall(r'<a class="result__url" href="([^"]+)">', html, re.IGNORECASE)
        titles = re.findall(r'<h2 class="result__title">.*?<a[^>]*>(.*?)</a>', html, re.IGNORECASE | re.DOTALL)
        
        results = []
        for i in range(min(8, len(snippets))):
            snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip()
            title = re.sub(r'<[^>]+>', '', titles[i]).strip() if i < len(titles) else "No Title"
            url_match = urls[i] if i < len(urls) else ""
            if 'uddg=' in url_match:
                url_match = urllib.parse.unquote(url_match.split('uddg=')[1].split('&')[0])
            results.append({'title': title, 'snippet': snippet, 'url': url_match})
        return results
    except Exception as e:
        print(f'Error for {query}: {e}')
        return []

queries = [
    "e-commerce impact on downtown retail vacancy rates",
    "national retail vacancy rate 2023 2024",
    "Chicago retail vacancy rate 2023 2024",
    "New York retail vacancy rate 2023 2024"
]

all_results = []
for q in queries:
    print(f"Searching: {q}")
    res = search(q)
    for r in res:
        r['query'] = q
        all_results.append(r)

with open('retail_results3.json', 'w') as f:
    json.dump(all_results, f, indent=2)
