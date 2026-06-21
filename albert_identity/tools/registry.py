"""
Centraliza todas as ferramentas (tools) disponíveis.
Mapeia os nomes da API para as funções Python e organiza os schemas.
"""

from typing import List, Dict, Callable, Any
from app.tools.calculator import execute_calculator, CALCULATOR_TOOL_SCHEMA

# Registry: nome → função
# Este dicionário conecta o nome que a Anthropic conhece com a função Python real.
TOOL_REGISTRY: Dict[str, Callable[[dict], str]] = {
    "symbolic_calculator": execute_calculator,
}

    # Futuras expansões (Fase 2):
    # "plot_function": execute_plotter,
    # "search_arxiv": execute_arxiv_search,


# Schemas: lista para a API
# Esta é a lista que enviamos para a Anthropic para ela saber o que o Albert pode fazer.
TOOL_SCHEMAS: List[Dict[str, Any]] = [
    CALCULATOR_TOOL_SCHEMA,
]

    # Futuras expansões (Fase 2):
    # PLOTTER_TOOL_SCHEMA,
    # ARXIV_SCHEMA,



# Função despachadora
def dispatch(tool_name: str, tool_input: dict) -> str:
    # 1. Busca a função correspondente no dicionário
    tool_fn = TOOL_REGISTRY.get(tool_name)

    # 2. Valida se a ferramenta existe
    if not tool_fn:
        return f"Erro: A ferramenta '{tool_name}' não está registrada no sistema do Albert."

    # 3. Tenta executar a ferramenta com os parâmetros fornecidos
    try:
        # Chama a função (ex: execute_calculator) passando o dict de inputs
        result = tool_fn(tool_input)
        return result

    except Exception as e:
        # Captura qualquer erro de execução para não travar o Agente
        return f"Erro crítico ao executar a ferramenta '{tool_name}': {str(e)}"