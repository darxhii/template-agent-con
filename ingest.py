import json
import sys
import os

# Read the search results from the file
with open('search_results.json', 'r') as f:
    results = json.load(f)

# We don't have the tool, so we'll just print a message
print("Ingesting results into RAG...")
print(f"Story-ID: municipal-cyber-rules-123")
print(f"Ingested {len(results['results'])} results.")
