"""
MCP Client — Connects to the MCP Care Guidelines server.

Supports two modes:
  1. HTTP REST client (default): calls the FastAPI endpoints on MCP_SERVER_HOST:MCP_SERVER_PORT
  2. MCP SDK client (when MCP_USE_SDK=true): connects via stdio to the MCP server process

The sync wrapper `get_care_guidelines_sync` is used by care_tools.py.
"""

import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

MCP_SERVER_HOST = os.getenv("MCP_SERVER_HOST", "localhost")
MCP_SERVER_PORT = os.getenv("MCP_SERVER_PORT", "8001")
MCP_BASE_URL = f"http://{MCP_SERVER_HOST}:{MCP_SERVER_PORT}"
MCP_USE_SDK = os.getenv("MCP_USE_SDK", "false").lower() == "true"


async def get_care_guidelines(symptoms: str) -> dict:
    """
    Appelle le serveur MCP et retourne les recommandations
    de soins pertinentes basées sur les symptômes.
    """
    if MCP_USE_SDK:
        return await _get_guidelines_via_sdk(symptoms)
    return await _get_guidelines_via_http(symptoms)


async def _get_guidelines_via_http(symptoms: str) -> dict:
    """Appelle le serveur MCP via HTTP REST."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{MCP_BASE_URL}/guidelines",
                params={"symptoms": symptoms},
            )
            response.raise_for_status()
            return response.json()
    except httpx.ConnectError:
        return {
            "status": "mcp_server_unavailable",
            "guidelines": [],
            "message": (
                "Le serveur MCP n'est pas disponible. "
                "Recommandations générales appliquées."
            ),
        }
    except Exception as e:
        return {
            "status": "error",
            "guidelines": [],
            "message": f"Erreur lors de la connexion au serveur MCP : {str(e)}",
        }


async def _get_guidelines_via_sdk(symptoms: str) -> dict:
    """Appelle le serveur MCP via le protocole MCP SDK (stdio)."""
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        server_params = StdioServerParameters(
            command="python",
            args=["-m", "mcp_server.server", "--mcp"],
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "get_care_guidelines",
                    arguments={"symptoms": symptoms},
                )
                content_text = result.content[0].text if result.content else "{}"
                return json.loads(content_text)
    except Exception as e:
        return {
            "status": "mcp_sdk_error",
            "guidelines": [],
            "message": f"Erreur MCP SDK : {str(e)}",
        }


def get_care_guidelines_sync(symptoms: str) -> dict:
    """
    Wrapper synchrone pour get_care_guidelines.
    Utilise httpx en mode synchrone pour éviter les problèmes
    avec les boucles d'événements existantes.
    """
    if MCP_USE_SDK:
        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(
                    asyncio.run, _get_guidelines_via_sdk(symptoms)
                ).result()
        return asyncio.run(_get_guidelines_via_sdk(symptoms))

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"{MCP_BASE_URL}/guidelines",
                params={"symptoms": symptoms},
            )
            response.raise_for_status()
            return response.json()
    except httpx.ConnectError:
        return {
            "status": "mcp_server_unavailable",
            "guidelines": [],
            "message": (
                "Le serveur MCP n'est pas disponible. "
                "Recommandations générales appliquées."
            ),
        }
    except Exception as e:
        return {
            "status": "error",
            "guidelines": [],
            "message": f"Erreur lors de la connexion au serveur MCP : {str(e)}",
        }
