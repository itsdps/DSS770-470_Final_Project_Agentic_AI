from ddgs import DDGS

def dd_search(q, max_results=1):
    try:
        results=DDGS().text(q, max_results=max_results)
        print("WEB SEARCH RESULTS>>>", results)
        if results:
            return results[0]["body"]
        else:
            return "No relevant information found."
    except Exception as e:
        print(f"Search error: {e}")
        return "Error: Could not retrieve search results."
    

if __name__ == '__main__':
    # Simple test
    print(dd_search("population of France"))
