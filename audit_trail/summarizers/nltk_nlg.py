from __future__ import annotations

import logging
from typing import Any, Dict

from django.conf import settings

try:  # pragma: no cover - optional dependency
    import nltk
except ImportError:  # pragma: no cover
    nltk = None

from .utils import describe_change

logger = logging.getLogger(__name__)

LANG_TOKENIZERS = {
    "en": "tokenizers/punkt/english.pickle",
    "de": "tokenizers/punkt/german.pickle",
    "es": "tokenizers/punkt/spanish.pickle",
    "fr": "tokenizers/punkt/french.pickle",
    "pt": "tokenizers/punkt/portuguese.pickle",
    "it": "tokenizers/punkt/italian.pickle",
}


def _load_tokenizer(resource: str):  # pragma: no cover - exercised via _tokenize
    if not nltk:
        return None
    try:
        return nltk.data.load(resource)
    except LookupError:
        for package in ("punkt", "punkt_tab"):
            try:
                nltk.download(package, quiet=True)
            except Exception:  # pragma: no cover - downloader failure
                logger.warning(
                    "Failed to download NLTK package %s", package, exc_info=True
                )
        try:
            return nltk.data.load(resource)
        except LookupError:
            fallback_resource = LANG_TOKENIZERS["en"]
            try:
                return nltk.data.load(fallback_resource)
            except LookupError:
                logger.error("Unable to load fallback NLTK tokenizer.")
                return None


def _tokenize(text: str, locale: str = "en") -> str:
    """Segment text using the locale-specific Punkt tokenizer if available."""

    if not text.strip() or not nltk:
        return text
    resource = LANG_TOKENIZERS.get(locale.lower(), LANG_TOKENIZERS["en"])
    tokenizer = _load_tokenizer(resource)
    if not tokenizer:
        return text
    return " ".join(tokenizer.tokenize(text))


def summarize(diff: Dict[str, Dict[str, Any]]) -> str:
    """Generate a locale-aware audit summary using NLTK sentence tokenization."""

    locale = getattr(settings, "AUDITTRAIL_SUMMARIZER_LOCALE", "en") or "en"
    normalized_locale = locale.lower()
    sentences = [
        describe_change(field, payload, locale=normalized_locale)
        for field, payload in diff.items()
    ]
    text = " ".join(sentence for sentence in sentences if sentence)
    return _tokenize(text, locale=normalized_locale)
