from rapidfuzz import fuzz

class EntityResolver:
    @staticmethod
    def resolve_platform_refs(asin: str, product_name: str) -> dict:
        # Stub implementation using rapidfuzz
        # In a real scenario, this would query external search APIs and match names
        # e.g., match = fuzz.ratio(product_name.lower(), external_result.lower())
        return {
            "amazon": [asin],
            "reddit": [f"search?q={product_name.replace(' ', '+')}"],
            "youtube": [f"results?search_query={product_name.replace(' ', '+')}"]
        }
