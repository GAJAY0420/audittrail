from __future__ import annotations

from importlib import import_module
from typing import Any, Dict

from django.conf import settings

_SUMMARIZER_MAP = {
    "grammar": "audit_trail.summarizers.grammar_nlg",
    "nltk": "audit_trail.summarizers.nltk_nlg",
    "multilang": "audit_trail.summarizers.multilang_nlg",
    "llm": "audit_trail.summarizers.llm_client",
}


def summarize(diff: Dict[str, Dict[str, Any]]) -> str:
    flavor = getattr(settings, "AUDITTRAIL_SUMMARIZER", "nltk")
    module_path = _SUMMARIZER_MAP.get(flavor, _SUMMARIZER_MAP["nltk"])
    module = import_module(module_path)
    if flavor == "llm":
        client = module.LLMClient()
        return client.summarize(diff)
    return module.summarize(diff)
