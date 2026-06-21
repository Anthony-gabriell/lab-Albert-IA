"""
Lógica do SymPy (sem dependências do projeto)
Executa cálculo simbólico usando SymPy.
Recebe uma expressão como string, processa e retorna o resultado.
"""

import sympy
from sympy import (
    symbols, sympify, latex, diff, integrate, solve,
    simplify, limit, series, factor, expand,
    sin, cos, tan, exp, log, sqrt, pi, E, I, oo,
    SympifyError
)

# Constante: variáveis simbólicas padrão
# Definimos os símbolos matemáticos comuns na física
x, y, z, t, r, theta, phi = symbols('x y z t r theta phi')
# n, m, k são tratados como inteiros (comum em somatórios e mecânica quântica)
n, m, k = symbols('n m k', integer=True)
# a, b, c são constantes reais
a, b, c = symbols('a b c', real=True)


# Função principal da tool
def execute_calculator(params: dict) -> str:

    # Recebe um dicionário de parâmetros e retorna uma string com o resultado.

    expression = params.get("expression", "")
    operation = params.get("operation", "evaluate")
    output_format = params.get("output_format", "latex")

    if not expression:
        return "Erro: Nenhuma expressão foi fornecida para cálculo."

    try:
        # Tenta executar a operação matemática
        result = _dispatch(expression, operation, output_format)
        return result
    except SympifyError:
        return f"Erro de sintaxe matemática: '{expression}'. Certifique-se de usar notação Python (ex: ** para potência)."
    except Exception as e:
        return f"Erro inesperado no cálculo: {str(e)}"


# Função despachadora (Privada)
def _dispatch(expression: str, operation: str, output_format: str) -> str:

    # Converte a string de entrada em um objeto matemático do SymPy
    expr = sympify(expression)
    result = None

    if operation in ["evaluate", "simplify"]:
        result = simplify(expr)

    elif operation in ["diff", "derivative"]:
        result = diff(expr, x)  # Derivada em relação a x por padrão

    elif operation in ["integrate", "integral"]:
        result = integrate(expr, x)  # Integral indefinida em relação a x

    elif operation in ["solve"]:
        result = solve(expr, x)  # Resolve para x (assume expr = 0)

    elif operation in ["factor"]:
        result = factor(expr)

    elif operation in ["expand"]:
        result = expand(expr)

    elif operation in ["limit"]:
        result = limit(expr, x, 0)  # Limite quando x tende a 0 por padrão

    else:
        return f"Operação '{operation}' não é suportada pelo Albert."

    # Formatação do resultado final
    if output_format == "latex":
        return f"Resultado: ${latex(result)}$"

    return f"Resultado: {str(result)}"


# Schema da tool (para a API da Anthropic)
CALCULATOR_TOOL_SCHEMA = {
    "name": "symbolic_calculator",
    "description": (
        "Executa cálculos matemáticos simbólicos avançados usando SymPy. "
        "Use para: derivadas, integrais, simplificações, resolução de equações, "
        "fatoração e limites. Prefira esta ferramenta para garantir precisão "
        "em derivações físicas complexas."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "A expressão matemática em notação Python (ex: 'diff(sin(x), x)' ou 'x**2').",
            },
            "operation": {
                "type": "string",
                "enum": ["evaluate", "diff", "integrate", "solve", "factor", "expand", "limit", "simplify"],
                "description": "A operação matemática a ser realizada.",
            },
            "output_format": {
                "type": "string",
                "enum": ["latex", "text"],
                "default": "latex",
                "description": "O formato da string de retorno.",
            },
        },
        "required": ["expression", "operation"],
    },
}