"""
MCP Client — Async and sync HTTP client connecting to the MCP Care Guidelines server.
"""

import os
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

MCP_SERVER_HOST = os.getenv("MCP_SERVER_HOST", "localhost")
MCP_SERVER_PORT = os.getenv("MCP_SERVER_PORT", "8001")
MCP_BASE_URL = f"http://{MCP_SERVER_HOST}:{MCP_SERVER_PORT}"


async def get_care_guidelines(symptoms: str) -> dict:
    """
    Appelle le serveur MCP local et retourne les recommandations
    de soins pertinentes basées sur les symptômes.

    Args:
        symptoms: Chaîne décrivant les symptômes du patient

    Returns:
        Dictionnaire contenant les recommandations de soins correspondantes
    """
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


def get_care_guidelines_sync(symptoms: str) -> dict:
    """
    Wrapper synchrone pour get_care_guidelines.
    Utilise httpx en mode synchrone pour éviter les problèmes
    avec les boucles d'événements existantes.

    Args:
        symptoms: Chaîne décrivant les symptômes du patient

    Returns:
        Dictionnaire contenant les recommandations de soins correspondantes
    """
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
