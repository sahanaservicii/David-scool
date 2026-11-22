"""agentos — офлайн-мультиагентная система для домашней инфраструктуры."""
from .core import VERSION, Registry, REGISTRY, load_agents, answer, make_context

__all__ = ["VERSION", "Registry", "REGISTRY", "load_agents", "answer",
           "make_context"]
__version__ = VERSION
