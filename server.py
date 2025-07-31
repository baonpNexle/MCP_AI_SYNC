from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("server")

# Constants
MERCHANT_STORE_API_BASE = "http://localhost:4001/MerchantStore"
MERCHANT_ID = "Tnc"

async def call_merchant_api(
        endpoint: str,
        payload: dict[str, Any]
        ) -> dict[str, Any] | None:
    """Make a request to the AI_SYNC weaviate Merchant_Store DB API with proper error handling."""
    url = f"{MERCHANT_STORE_API_BASE}/{endpoint}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url,json=payload, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"API call to {url} failed: {e}")
            return None
        

@mcp.tool()
async def findAllStores() -> str:
    """Find all stores under a merchantID class
    Args:
        merchantID: string
    """
    url = f"findAllStores"
    payload = { "merchantId": MERCHANT_ID }
    data = await call_merchant_api(url, payload)

    if not data or "data" not in data:
        return "No stores found or invalid merchant ID."

    stores = data["data"]
    if not stores:
        return "Merchant has no stores."

    store_list = "\n".join([f"- {entry['name']}" for entry in stores])
    return f"Stores under {MERCHANT_ID}:\n{store_list}"  


@mcp.tool()
async def findStore(queryText: str) -> str:
    """Search for relevant stores under a merchant using a natural language query.
    
    Args:
        merchantID: The merchant class to search under (e.g., "Tnc").
        queryText: A natural language description of the desired product or store.
    """
    payload = {
        "merchantId": MERCHANT_ID,
        "queryText": queryText
    }
    data = await call_merchant_api("findStore", payload)

    if not data or "data" not in data:
        return "No results found or invalid request."

    results = data["data"]
    if not results:
        return "No matching stores found."

    top_matches = "\n\n".join([
        f"Name: {r['name']}\nScore: {r['_additional']['score']}\nDescription: {r['fullOriginContent']}"
        for r in results[:5]  # Return top 5 matches only for brevity
    ])
    return f"Top results for '{queryText}' under {MERCHANT_ID}:\n\n{top_matches}"


@mcp.tool()
async def addNewStore(
    name: str,
    keywords: list[str],
    fullOriginContent: str,
    fullTextSearch: str
) -> str:
    """Add a new store to the merchant's database.
    
    Args:
        merchantID: The merchant to which the store belongs (e.g., "tnc").
        name: Full name of the store.
        keywords: List of keywords describing the store.
        fullOriginContent: Full description of the store.
        fullTextSearch: Preprocessed text for search indexing.
    """
    payload = {
        "merchantId": MERCHANT_ID,
        "storeData": {
            "name": name,
            "keywords": keywords,
            "fullOriginContent": fullOriginContent,
            "fullTextSearch": fullTextSearch
        }
    }

    data = await call_merchant_api("addNewStore", payload)

    if not data or "data" not in data or "id" not in data["data"]:
        return "Failed to add new store."

    return f"New store added successfully. Store ID: {data['data']['id']}"

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')