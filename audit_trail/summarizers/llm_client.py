"""Provider-aware LLM summarizer client."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Iterable, List

import boto3
import httpx
from django.conf import settings

from .utils import describe_change

logger = logging.getLogger(__name__)

OPENAI_DEFAULT_ENDPOINT = "https://api.openai.com/v1/chat/completions"
CLAUDE_DEFAULT_ENDPOINT = "https://api.anthropic.com/v1/messages"
GEMINI_DEFAULT_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_SYSTEM_PROMPT = (
    "You are an audit assistant. Summarize the following field-level deltas in a "
    "single concise paragraph while preserving key numbers, statuses, and actors."
)
BEDROCK_MODEL_ALIASES = {
    "claude-3-haiku": "anthropic.claude-3-haiku-20240307-v1:0",
    "anthropic.claude-3-haiku": "anthropic.claude-3-haiku-20240307-v1:0",
    "anthropic.claude-3-haiku-20240307-v1:0": "anthropic.claude-3-haiku-20240307-v1:0",
    "claude-haiku": "anthropic.claude-3-haiku-20240307-v1:0",
    "claude-3-sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",
    "anthropic.claude-3-sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",
    "anthropic.claude-3-sonnet-20240229-v1:0": "anthropic.claude-3-sonnet-20240229-v1:0",
    "claude-sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",
    "claude-3-opus": "anthropic.claude-3-opus-20240229-v1:0",
    "anthropic.claude-3-opus": "anthropic.claude-3-opus-20240229-v1:0",
    "anthropic.claude-3-opus-20240229-v1:0": "anthropic.claude-3-opus-20240229-v1:0",
    "claude-opus": "anthropic.claude-3-opus-20240229-v1:0",
    "nova-lite": "amazon.nova-2-lite-v1:0",
    "amazon.nova-lite": "amazon.nova-2-lite-v1:0",
    "amazon.nova-lite-1.0": "amazon.nova-2-lite-v1:0",
    "amazon.nova-lite-v1:0": "amazon.nova-2-lite-v1:0",
    "nova-micro": "amazon.nova-micro-v1:0",
    "amazon.nova-micro": "amazon.nova-micro-v1:0",
    "amazon.nova-micro-1.0": "amazon.nova-micro-v1:0",
    "amazon.nova-micro-v1:0": "amazon.nova-micro-v1:0",
    "nova-pro": "amazon.nova-pro-v1:0",
    "amazon.nova-pro": "amazon.nova-pro-v1:0",
    "amazon.nova-pro-v1:0": "amazon.nova-pro-v1:0",
}


class LLMClient:
    """Generate summaries via HTTP, OpenAI, Claude, Gemini, or AWS Bedrock."""

    def __init__(self) -> None:
        self.provider = getattr(settings, "AUDITTRAIL_LLM_PROVIDER", "http").lower()
        self.endpoint = getattr(settings, "AUDITTRAIL_LLM_ENDPOINT", "").rstrip("/")
        self.api_key = getattr(settings, "AUDITTRAIL_LLM_TOKEN", "")
        raw_model = getattr(settings, "AUDITTRAIL_LLM_MODEL", "")
        self.model = self._normalize_model_id(raw_model)
        self.locale = getattr(settings, "AUDITTRAIL_SUMMARIZER_LOCALE", "en")
        self.system_prompt = getattr(
            settings, "AUDITTRAIL_LLM_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT
        )
        # self.role = getattr(settings, "AUDITTRAIL_LLM_ROLE", "audit_summarizer")
        self.max_tokens = int(getattr(settings, "AUDITTRAIL_LLM_MAX_TOKENS", 256))
        self.temperature = float(getattr(settings, "AUDITTRAIL_LLM_TEMPERATURE", 0.1))
        self.top_p = float(getattr(settings, "AUDITTRAIL_LLM_TOP_P", 0.9))
        self.bedrock_region = getattr(
            settings, "AUDITTRAIL_BEDROCK_REGION", "us-east-1"
        )
        self.bedrock_access_key = getattr(settings, "AUDITTRAIL_BEDROCK_ACCESS_KEY", "")
        self.bedrock_secret_key = getattr(settings, "AUDITTRAIL_BEDROCK_SECRET_KEY", "")
        self.bedrock_session_token = getattr(
            settings, "AUDITTRAIL_BEDROCK_SESSION_TOKEN", ""
        )
        self._bedrock_client = None

        self._apply_default_endpoints()
        self._validate_configuration()

    def summarize(self, diff: Dict[str, Dict[str, Any]]) -> str:
        prompt = self._build_prompt(diff)
        logger.debug("Using LLM provider %s", self.provider)
        if self.provider == "openai":
            return self._summarize_openai(prompt)
        if self.provider == "claude":
            return self._summarize_claude(prompt)
        if self.provider == "gemini":
            return self._summarize_gemini(prompt)
        if self.provider == "bedrock":
            return self._summarize_bedrock(prompt)
        if self.provider == "http":
            return self._summarize_http(diff, prompt)
        raise RuntimeError(f"Unsupported LLM provider: {self.provider}")

    # ------------------------------------------------------------------
    # Provider helpers
    # ------------------------------------------------------------------
    def _summarize_http(self, diff: Dict[str, Dict[str, Any]], prompt: str) -> str:
        payload = {"diff": diff, "prompt": prompt, "locale": self.locale}
        response = self._post(
            self.endpoint,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=payload,
            timeout=15.0,
        )
        return self._extract_plain_summary(response)

    def _summarize_openai(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
        }
        response = self._post(self.endpoint, headers=headers, json=body)
        return self._extract_openai_summary(response)

    def _summarize_claude(self, prompt: str) -> str:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "messages": [{"role": "user", "content": prompt}],
        }
        if self.system_prompt:
            body["system"] = self.system_prompt
        response = self._post(self.endpoint, headers=headers, json=body)
        return self._extract_claude_summary(response)

    def _summarize_gemini(self, prompt: str) -> str:
        headers = {
            "x-goog-api-key": self.api_key,
            "content-type": "application/json",
        }
        body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "maxOutputTokens": self.max_tokens,
                "temperature": self.temperature,
                "topP": self.top_p,
            },
        }
        url = f"{self.endpoint}/{self.model}:generateContent"
        response = self._post(url, headers=headers, json=body)
        return self._extract_gemini_summary(response)

    def _summarize_bedrock(self, prompt: str) -> str:
        client = self._get_bedrock_client()
        request_body = self._build_bedrock_request(prompt)
        response = client.invoke_model(
            modelId=getattr(settings, "AUDITTRAIL_BEDROCK_INFERENCE_MODEL", self.model),
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json",
        )
        raw_body = response.get("body")
        if hasattr(raw_body, "read"):
            payload = json.loads(raw_body.read().decode("utf-8"))
        else:
            payload = json.loads(raw_body or "{}")
        return self._extract_bedrock_summary(payload)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def _build_prompt(self, diff: Dict[str, Dict[str, Any]]) -> str:
        sentences = self._format_sentences(diff.items())
        bullet_list = "\n".join(f"- {sentence}" for sentence in sentences)
        locale_hint = self.locale.upper()
        return (
            f"Summarize the following audit changes in {locale_hint} using one "
            f"short paragraph.\n{bullet_list}"
        )

    def _format_sentences(
        self, items: Iterable[tuple[str, Dict[str, Any]]]
    ) -> List[str]:
        sentences: List[str] = []
        for field, payload in items:
            sentence = describe_change(field, payload, locale=self.locale)
            if sentence:
                sentences.append(sentence)
        return sentences or ["No material changes recorded."]

    def _post(
        self,
        url: str,
        *,
        headers: Dict[str, str],
        json: Dict[str, Any],
        timeout: float = 20.0,
    ) -> Dict[str, Any]:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, headers=headers, json=json)
            response.raise_for_status()
            return response.json()

    def _apply_default_endpoints(self) -> None:
        if self.provider == "openai" and not self.endpoint:
            self.endpoint = OPENAI_DEFAULT_ENDPOINT
        elif self.provider == "claude" and not self.endpoint:
            self.endpoint = CLAUDE_DEFAULT_ENDPOINT
        elif self.provider == "gemini" and not self.endpoint:
            self.endpoint = GEMINI_DEFAULT_ENDPOINT
        elif self.provider == "bedrock" and not self.endpoint:
            if not self.model:
                raise RuntimeError(
                    "AUDITTRAIL_LLM_MODEL must be set for Bedrock provider"
                )
            self.endpoint = (
                f"https://bedrock-runtime.{self.bedrock_region}.amazonaws.com/"
                f"model/{self.model}/invoke"
            )

    def _validate_configuration(self) -> None:
        if self.provider == "http":
            if not self.endpoint or not self.api_key:
                raise RuntimeError("LLM endpoint not configured")
        elif self.provider in {"openai", "claude"}:
            if not self.api_key:
                raise RuntimeError(
                    "AUDITTRAIL_LLM_TOKEN must be set for the selected provider"
                )
            if not self.model:
                raise RuntimeError("AUDITTRAIL_LLM_MODEL is required for this provider")
        elif self.provider == "gemini":
            if not self.api_key:
                raise RuntimeError("AUDITTRAIL_LLM_TOKEN must carry the Gemini API key")
            if not self.model:
                raise RuntimeError("AUDITTRAIL_LLM_MODEL is required for Gemini")
        elif self.provider == "bedrock":
            if not self.model:
                raise RuntimeError("AUDITTRAIL_LLM_MODEL must be set for Bedrock")
        else:
            raise RuntimeError(f"Unsupported LLM provider: {self.provider}")

    @staticmethod
    def _extract_plain_summary(response: Dict[str, Any]) -> str:
        return str(response.get("summary", "")).strip()

    @staticmethod
    def _extract_openai_summary(response: Dict[str, Any]) -> str:
        choices = response.get("choices", [])
        if not choices:
            return ""
        message = choices[0].get("message", {})
        return str(message.get("content", "")).strip()

    @staticmethod
    def _extract_claude_summary(response: Dict[str, Any]) -> str:
        content = response.get("content", [])
        texts = [block.get("text", "") for block in content if isinstance(block, dict)]
        return "\n".join(filter(None, texts)).strip()

    @staticmethod
    def _extract_gemini_summary(response: Dict[str, Any]) -> str:
        candidates = response.get("candidates", [])
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        texts = [part.get("text", "") for part in parts if isinstance(part, dict)]
        return "\n".join(filter(None, texts)).strip()

    @staticmethod
    def _extract_bedrock_summary(response: Dict[str, Any]) -> str:
        if "outputText" in response:
            return str(response["outputText"]).strip()
        if "content" in response and isinstance(response["content"], list):
            texts = []
            for block in response["content"]:
                if isinstance(block, dict):
                    text_value = block.get("text")
                    if isinstance(text_value, str):
                        texts.append(text_value)
                    elif isinstance(text_value, list):
                        texts.extend(str(item) for item in text_value)
            if texts:
                return "\n".join(texts).strip()
        if "output" in response and isinstance(response["output"], dict):
            blocks = response["output"].get("message", {}).get("content", [])
            texts = []
            for block in blocks:
                if isinstance(block, dict):
                    text_value = block.get("text")
                    if isinstance(text_value, str):
                        texts.append(text_value)
                    elif isinstance(text_value, list):
                        texts.extend(str(item) for item in text_value)
            if texts:
                return "\n".join(texts).strip()
        return str(response.get("summary", "")).strip()

    def _get_bedrock_client(self):  # pragma: no cover - network-heavy
        if self._bedrock_client is not None:
            return self._bedrock_client
        client_kwargs: Dict[str, Any] = {"region_name": self.bedrock_region}
        if self.bedrock_access_key and self.bedrock_secret_key:
            client_kwargs.update(
                aws_access_key_id=self.bedrock_access_key,
                aws_secret_access_key=self.bedrock_secret_key,
            )
            if self.bedrock_session_token:
                client_kwargs["aws_session_token"] = self.bedrock_session_token
        self._bedrock_client = boto3.client("bedrock-runtime", **client_kwargs)
        return self._bedrock_client

    def _build_bedrock_request(self, prompt: str) -> Dict[str, Any]:
        if self.model.startswith("anthropic."):
            request: Dict[str, Any] = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "top_p": self.top_p,
                "messages": [
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": prompt}],
                    }
                ],
            }
            if self.system_prompt:
                request["system"] = self.system_prompt
            return request
        request: Dict[str, Any] = {
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": prompt}],
                }
            ],
            "inferenceConfig": {
                "maxTokens": self.max_tokens,
                "temperature": self.temperature,
                "topP": self.top_p,
            },
        }
        if self.system_prompt:
            request["system"] = [{"text": self.system_prompt}]
        return request

    def _normalize_model_id(self, model: str) -> str:
        if not model:
            return model
        key = model.strip().lower().replace("_", "-")
        key = key.replace(" ", "")
        return BEDROCK_MODEL_ALIASES.get(key, model)
