"""
Função que controi o system prompt final combinando base + fragmentos.
É o único arquivo que sabe "quais pedaços usar em qual situação".
"""

from typing import Optional, Dict, Any
from albert_identity.prompts.base import ALBERT_BASE_SYSTEM_PROMPT
from albert_identity.prompts.fragments import (
    REASONING_TRANSPARENCY_FRAGMENT,
    PHYSICS_EXAMPLES_FRAGMENT,
    RAG_CONTEXT_FRAGMENT,
    CONSCIOUSNESS_FRAGMENT,
    TOOL_USAGE_FRAGMENT,
)

def build_system_prompt(
    include_reasoning_transparency: bool = True,
    include_extra_examples: bool = False,
    include_tool_usage: bool = False,
    include_rag_context: bool = False,
    rag_context: Optional[str] = None,
    include_consciousness: bool = False,
    consciousness_data: Optional[Dict[str,Any]] = None,
) -> str:

    # Monta o System Prompt final de forma modular.
    # Começamos com a base imutável (o DNA do Albert)
    parts = [ALBERT_BASE_SYSTEM_PROMPT]

    # Injetamos transparência de raciocínio se solicitado
    if include_reasoning_transparency:
        parts.append(REASONING_TRANSPARENCY_FRAGMENT)

    # Injetamos exemplos extras para reforçar o comportamento
    if include_extra_examples:
        parts.append(PHYSICS_EXAMPLES_FRAGMENT)

    # Injetamos instruções de uso de ferramentas (como usr uma HP50g)
    if include_tool_usage:
        parts.append(TOOL_USAGE_FRAGMENT)

    # Injetamos contexto recuperado (Futuramente vai receber o RAG)
    if include_rag_context and rag_context:
        formatted_rag = RAG_CONTEXT_FRAGMENT.format(context=rag_context)
        parts.append(formatted_rag)

    # Injetamos estado de consciência (Essa parte eu vou construir ainda fase 4 ou 5)
    if include_consciousness and consciousness_data:
        formatted_consciousness = CONSCIOUSNESS_FRAGMENT.format(
            mood=consciousness_data.get("mood", "neutral"),
            recent_topics=consciousness_data.get("recent_topics", "none"),
            environment=consciousness_data.get("environment", "stable"),
        )
        parts.append(formatted_consciousness)

    # Junta todos os blocos com espaçamento duplo para clareza
    return "\n\n".join(parts)

def get_basic_system_prompt() -> str:

    # Atalho para o V0.1 do Albert.
    # Ativa apenas o necessário para a fase inicial: Personalidade + Raciocínio + Ferramentas.

    return build_system_prompt(
        include_reasoning_transparency=True,
        include_tool_usage=True,
        include_extra_examples=False,
        include_rag_context=False,
        include_consciousness=False
    )