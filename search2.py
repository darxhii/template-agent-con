import urllib.request
import urllib.parse
import re

def search(query):
    url = 'https://html.duckduckgo.com/html/?q=' + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        html = urllib.request.urlopen(req).read().decode('utf-8')
        snippets = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', html, re.IGNORECASE | re.DOTALL)
        urls = re.findall(r'<a class="result__url" href="([^"]+)">', html, re.IGNORECASE)
        
        results = []
        for i in range(min(5, len(snippets))):
            snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip()
            url = urllib.parse.unquote(urls[i].split('uddg=')[1].split('&')[0]) if 'uddg=' in urls[i] else urls[i]
            results.append({'snippet': snippet, 'url': url})
        return results
    except Exception as e:
        return []

queries = [
    "Columbia University require professors AI rules course syllabi",
    "University of Utah require professors AI rules course syllabi",
    "Turnitin GPTZero Copyleaks unreliable false positive rates biases non-native English speakers neurodiverse"
]

for q in queries:
    print(f"Query: {q}")
    res = search(q)
    for r in res:
        print(f" - {r['snippet']} ({r['url']})")
    print()
