import logging
import time
from typing import List, Dict, Any, Optional

from langchain_core.tools import tool
from serpapi import GoogleSearch

from settings import SharedSettings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger(__name__)


@tool
def search_google_informations(query: str) -> List[Dict[str, Any]]:
    """
    Use esta ferramenta para pesquisar informações sobre código, dúvidas de melhorias ou algo do tipo.
    Priorize retornos de sites como Stackoverflow, Anthropic, MDN Web Docs. Use o nome do site na query para aumentar a qualidade da pesquisa

    Args:
        query (str): Termo de busca

    Returns:
        List[Dict[str, Any]]: Lista com os resultados orgânicos da busca
    """
    try:
        if not hasattr(SharedSettings, 'SERPAPI_API_KEY') or not SharedSettings.SERPAPI_API_KEY:
            logger.error("SERPAPI_API_KEY não encontrada ou vazia")
            return []

        params = {
            "engine": "google",
            "q": f"{query}",
            "api_key": SharedSettings.SERPAPI_API_KEY,
            "num": 10
        }

        logger.info(f"Searching Google for: {query}")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                search = GoogleSearch(params)
                results = search.get_dict()
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Tentativa {attempt + 1} falhou: {e}. Tentando novamente...")
                    time.sleep(1)
                else:
                    raise e

        organic_results = results.get("organic_results", [])
        if not organic_results:
            logger.warning("Nenhum resultado orgânico encontrado")
            return []

        filtered_results = []
        for result in organic_results:
            filtered_result = {
                "title": result.get("title", "Título não disponível"),
                "link": result.get("link", ""),
                "snippet": result.get("snippet", "Snippet não disponível"),
                "position": result.get("position", 0),
                "displayed_link": result.get("displayed_link", "")
            }
            filtered_results.append(filtered_result)

        logger.info(f"Encontrados {len(filtered_results)} resultados")
        return filtered_results

    except ImportError as e:
        error_msg = f"Erro de importação - certifique-se de que 'google-search-results' está instalado: {e}"
        logger.error(error_msg)
        return []

    except KeyError as e:
        error_msg = f"Chave não encontrada nos resultados: {e}"
        logger.error(error_msg)
        return []

    except Exception as e:
        error_msg = f"Erro ao processar busca: {e}"
        logger.error(error_msg)
        return []