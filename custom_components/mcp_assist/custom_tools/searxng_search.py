"""SearXNG Search custom tool for ha-lmstudio-mcp."""
import aiohttp
import asyncio
import logging
from typing import Dict, Any, List
from urllib.parse import urljoin
_LOGGER = logging.getLogger(__name__)

class SearXNGSearchTool:
    """SearXNG Search API tool."""

    def __init__(self, hass, local_url=None):
        """Initialize SearXNG Search tool."""
        self.hass = hass
        # Use provided API key - no fallback for security
        self.local_url = urljoin(local_url, "search")

    async def initialize(self):
        """Initialize the tool."""
        pass  # No logging needed

    def handles_tool(self, tool_name: str) -> bool:
        """Check if this class handles the given tool."""
        return tool_name == "search"

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get MCP tool definition for Brave Search."""
        return [{
            "name": "search",
            "description": "Search the web for current information using Brave Search",
            "inputSchema": {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    },
                    "count": {
                        "type": "number",
                        "description": "Number of results to return (default 5, max 20)",
                        "minimum": 1,
                        "maximum": 20,
                        "default": 5
                    }
                },
                "required": ["query"],
                "additionalProperties": False
            }
        }]

    async def handle_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute SearXNG Search."""
        query = arguments.get("query")
        count = min(arguments.get("count", 5), 20)  # Enforce max limit

        _LOGGER.debug(f"SearXNG Search: '{query}' (count: {count})")

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key
        }

        # Fix: Convert all values to strings for URL parameters
        params = {
            "q": query,
            "format": "json"
            "language": "en",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.base_url,
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        error = await response.text()
                        _LOGGER.error(f"SearXNG Search error {response.status}: {error}")
                        return {
                            "content": [{
                                "type": "text",
                                "text": f"❌ Search failed (HTTP {response.status}): {error[:200]}"
                            }]
                        }

                    data = await response.json()

                    # Format results for LLM
                    results = []
                    for item in data.get("web", {}).get("results", [])[:count]:
                        results.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "description": item.get("content", "")
                        })

                    # Format as text for the LLM
                    text_results = f"🔍 Search results for '{query}':\n\n"
                    for i, result in enumerate(results, 1):
                        text_results += f"{i}. **{result['title']}**\n"
                        text_results += f"   {result['url']}\n"
                        text_results += f"   {result['description']}\n\n"

                    return {
                        "content": [{
                            "type": "text",
                            "text": text_results
                        }]
                    }

        except asyncio.TimeoutError:  # Fix: Correct exception
            _LOGGER.error("SearXNG Search timeout")
            return {
                "content": [{
                    "type": "text",
                    "text": "❌ Search timeout - please try again"
                }]
            }
        except Exception as e:
            _LOGGER.error(f"SearXNG Search exception: {e}")
            return {
                "content": [{
                    "type": "text",
                    "text": f"❌ Search error: {str(e)}"
                }]
            }