"""
LLM Client - Unified interface for FPT AI (Saola)
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
import threading
from openai import OpenAI
from app.core import settings, logger

# LLM call logging configuration
LLM_LOG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs", "llm_calls"
)
os.makedirs(LLM_LOG_DIR, exist_ok=True)

# Global call counter for this session
_llm_call_counter = 0

# Session start time - used for log filename
_session_start_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _log_llm_call(
    call_type: str,
    messages: List[Dict],
    response: str,
    kwargs: Dict,
    duration_ms: float = 0,
):
    """Log LLM call to file for debugging"""
    global _llm_call_counter
    _llm_call_counter += 1

    timestamp = datetime.now()
    time_str = timestamp.strftime("%H:%M:%S.%f")[:-3]

    # Create log file for this session (includes start time)
    log_file = os.path.join(LLM_LOG_DIR, f"llm_calls_{_session_start_time}.log")

    # Build log entry
    separator = "=" * 80
    log_entry = f"""
{separator}
📤 LLM CALL #{_llm_call_counter} | {time_str} | Type: {call_type}
{separator}

🔧 PARAMETERS:
- Model: {kwargs.get('model', 'N/A')}
- Temperature: {kwargs.get('temperature', 'N/A')}
- Max Tokens: {kwargs.get('max_tokens', 'N/A')}
- JSON Mode: {kwargs.get('response_format', 'No')}
- Duration: {duration_ms:.0f}ms

📝 MESSAGES SENT:
"""

    for i, msg in enumerate(messages):
        role = msg.get("role", "unknown").upper()
        content = msg.get("content", "")
        # Truncate very long content for readability
        if len(content) > 50000:
            content = (
                content[:50000]
                + f"\n... [TRUNCATED - total {len(msg.get('content', ''))} chars]"
            )
        log_entry += f"""
--- [{role}] ---
{content}
"""

    # Add response
    response_display = response
    if len(response) > 50000:
        response_display = (
            response[:50000] + f"\n... [TRUNCATED - total {len(response)} chars]"
        )

    log_entry += f"""
📥 RESPONSE:
{response_display}

{separator}
"""

    # Write to file
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
        logger.debug(f"📝 LLM Call #{_llm_call_counter} logged to {log_file}")
    except Exception as e:
        logger.error(f"❌ Failed to log LLM call: {e}")

    # Also log summary to console
    logger.info(
        f"📤 LLM Call #{_llm_call_counter} | {call_type} | {duration_ms:.0f}ms | Response: {len(response)} chars"
    )


class LLMClient:
    """
    Unified LLM client for FPT AI (Saola 3.1)
    Provides a clean interface for all LLM operations
    """

    def __init__(self):
        self.client = OpenAI(
            api_key=settings.FPT_API_KEY, base_url=settings.FPT_BASE_URL
        )
        self.model = settings.FPT_MODEL_NAME
        self.temperature = settings.FPT_TEMPERATURE
        self.max_tokens = settings.FPT_MAX_TOKENS

        logger.info(f"[OK] LLM Client initialized (Model: {self.model})")

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = None,
        max_tokens: int = None,
        json_mode: bool = False,
    ) -> str:
        """
        Send chat request to LLM

        Args:
            messages: List of {"role": "system"|"user"|"assistant", "content": "..."}
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            json_mode: Request JSON output format

        Returns:
            LLM response text
        """
        import time

        # Validate input type - catch common mistakes early
        if isinstance(messages, str):
            raise TypeError(
                "chat() requires List[Dict[str, str]], got string. "
                "Use complete() for string prompts or wrap: [{'role': 'user', 'content': your_string}]"
            )

        if not isinstance(messages, list):
            raise TypeError(f"messages must be list, got {type(messages)}")

        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature or self.temperature,
                "max_tokens": max_tokens or self.max_tokens,
            }

            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            start_time = time.time()
            response = self.client.chat.completions.create(**kwargs)
            duration_ms = (time.time() - start_time) * 1000

            response_text = response.choices[0].message.content

            # Log the call
            _log_llm_call(
                call_type="chat",
                messages=messages,
                response=response_text,
                kwargs=kwargs,
                duration_ms=duration_ms,
            )

            return response_text

        except Exception as e:
            logger.error(f"❌ LLM Chat Error: {e}")
            raise

    def complete(
        self,
        prompt: str,
        system_prompt: str = None,
        temperature: float = None,
        max_tokens: int = None,
        json_mode: bool = False,
    ) -> str:
        """
        Simple completion interface

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Override default
            max_tokens: Override default
            json_mode: Request JSON output

        Returns:
            LLM response text
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        return self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=json_mode,
        )

    def extract_json(self, prompt: str, system_prompt: str = None) -> Dict[str, Any]:
        """
        Extract structured JSON from LLM response

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt

        Returns:
            Parsed JSON dict
        """
        import json
        import re

        response = self.complete(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.1,  # Low temp for structured output
            json_mode=True,
        )

        try:
            # Try direct parse
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response)
            if json_match:
                return json.loads(json_match.group(1))

            # Try to find JSON object
            json_match = re.search(r"\{[\s\S]*\}", response)
            if json_match:
                return json.loads(json_match.group(0))

            logger.error(f"❌ Failed to parse JSON: {response[:200]}")
            return {}


# Global singleton
llm_client = LLMClient()


def get_llm_client() -> LLMClient:
    """Dependency for FastAPI"""
    return llm_client
