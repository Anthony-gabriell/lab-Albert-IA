"""
physics_tools.py — Wrapper exposing Albert's symbolic calculator as an
Odysseus agent tool using the same OpenAI function-call pattern as the
other tools in this package.
"""

import asyncio
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class SymbolicCalculatorTool:
    """Wraps albert_identity.tools.calculator.execute_calculator."""

    async def execute(self, params: Dict[str, Any], **_kwargs) -> str:
        try:
            from albert_identity.tools.calculator import execute_calculator
            result = await asyncio.to_thread(execute_calculator, params)
            return result
        except ImportError as e:
            logger.error(f"Albert calculator unavailable: {e}")
            return f"Error: symbolic_calculator is not available ({e})"
        except Exception as e:
            logger.error(f"symbolic_calculator error: {e}")
            return f"Error running symbolic_calculator: {e}"


# OpenAI function-call schema for this tool (matches FUNCTION_TOOL_SCHEMAS format)
SYMBOLIC_CALCULATOR_SCHEMA = {
    "type": "function",
    "function": {
        "name": "symbolic_calculator",
        "description": (
            "Execute advanced symbolic math using SymPy. Use for derivatives, "
            "integrals, simplifications, equation solving, factoring, and limits. "
            "Prefer this over manual calculation for complex physics derivations."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression in Python notation (e.g. 'sin(x)**2 + cos(x)**2')",
                },
                "operation": {
                    "type": "string",
                    "enum": ["evaluate", "diff", "integrate", "solve", "factor", "expand", "limit", "simplify"],
                    "description": "Operation to perform",
                },
                "output_format": {
                    "type": "string",
                    "enum": ["latex", "text"],
                    "description": "Return format — 'latex' (default) or 'text'",
                },
            },
            "required": ["expression", "operation"],
        },
    },
}
