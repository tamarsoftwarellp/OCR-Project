import time
import random
import logging
import re
from groq import Groq
from . import config     # Pulls configurations dynamically from your config.py

# 1. API Key Pool for Free Tier Automation
GROQ_KEYS_POOL = [
    config.GROQ_API_KEY,  # Uses your active fresh key ending in ...xaJp0
    # "gsk_PASTE_YOUR_SECOND_FREE_ACCOUNT_KEY_HERE"
]

current_key_idx = 0


class LLMJsonValidationError(Exception):
    """Raised when Groq's strict JSON mode itself rejects the model's
    output (code=json_validate_failed) - a non-429, non-retryable-by-default
    error. Groq still hands back the malformed text it rejected under
    'failed_generation' in the error body; we carry that through here so the
    caller can run it through our EXISTING local JSON repair pipeline
    (_repair_json_text / _repair_malformed_json_keys in parser.py) instead of
    losing the whole document to an empty fallback payload."""

    def __init__(self, message: str, failed_generation: str | None = None):
        super().__init__(message)
        self.failed_generation = failed_generation


def _extract_failed_generation(error_text: str) -> str | None:
    """Groq embeds the malformed model output verbatim under
    'failed_generation' inside the error body, e.g.:
        {'error': {..., 'failed_generation': '{...malformed json...}'}}
    Pull that raw text out so it can be repaired locally rather than thrown
    away."""
    match = re.search(r"'failed_generation':\s*'(.*)'\s*\}\s*\}\s*$", error_text, re.DOTALL)
    if not match:
        return None
    raw = match.group(1)
    # str(exception) renders real control chars as Python escape literals
    # (\n, \t, \') - decode those back to get real, parseable JSON text.
    try:
        return raw.encode("utf-8").decode("unicode_escape")
    except Exception:
        return raw

def get_current_client():
    """Instantiates a client using the currently active API key slot."""
    global current_key_idx
    return Groq(api_key=GROQ_KEYS_POOL[current_key_idx])

def call_groq_with_resilience(system_prompt: str, user_prompt: str) -> tuple:
    """Executes calls incorporating dynamic token scaling, safe pacing, and key rotation."""
    global current_key_idx
    retry = 0
    backoff = config.INITIAL_BACKOFF

    # --- STEP 1: Dynamic Token Budgeting for Free Tier Protection ---
    # Safe character-to-token fallback calculation (1 token ≈ 3.2 chars)
    total_chars = len(system_prompt) + len(user_prompt)
    estimated_input_tokens = int(total_chars / 3.2)
    
    # 12,000 Free TPM limit - Input Tokens - 600 safety gap
    computed_safe_tokens = 12000 - estimated_input_tokens - 600
    
    # Restrict max_tokens bounds dynamically using config settings
    if computed_safe_tokens < 1500:
        dynamic_max_tokens = 1500  # Emergency minimum floor for clean JSON printing
    elif computed_safe_tokens > config.MAX_OUTPUT_TOKENS:
        dynamic_max_tokens = config.MAX_OUTPUT_TOKENS  # Cap it at your defined 4000 limit
    else:
        dynamic_max_tokens = computed_safe_tokens

    while retry < config.MAX_RETRIES:
        client = get_current_client()
        try:
            response = client.chat.completions.create(
                model=config.MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"} if config.STRICT_JSON_MODE else None,
                temperature=0.1,
                max_tokens=int(dynamic_max_tokens),  # Injects dynamic safety budget
                timeout=config.REQUEST_TIMEOUT
            )
            
            # --- STEP 2: Strict Pacing Cooldown to Prevent 429 Errors ---
            # Delays execution slightly to keep calls safely beneath the 30 RPM ceiling
            time.sleep(3.5)
            return response

        except Exception as e:
            error_msg = str(e).lower()
            
            # Catch account exhaustion walls (TPD Limit or heavy running windows)
            if "tokens per day" in error_msg or "tpd" in error_msg or "limit reached" in error_msg:
                logging.warning(f"🚨 Slot #{current_key_idx} exhausted its limit or ran out of daily tokens.")
                
                # Check if multiple keys are populated to rotate automatically
                if len(GROQ_KEYS_POOL) > 1:
                    current_key_idx = (current_key_idx + 1) % len(GROQ_KEYS_POOL)
                    logging.info(f"🔄 Rotating to Free API Key Slot #{current_key_idx}...")
                    time.sleep(1.5)  # Quick breathing window before retrying file
                    continue
                else:
                    logging.error("❌ Daily budget exhausted and no backup keys are configured in GROQ_KEYS_POOL.")
                    raise e
            
            # Catch standard concurrent RPM triggers
            elif "429" in error_msg or "rate limit" in error_msg:
                sleep_time = (backoff ** retry) + random.uniform(0.1, 0.9)
                logging.warning(f"Groq Rate Limit (429) hit. Backing off via Jitter for {round(sleep_time, 2)}s...")
                time.sleep(sleep_time)
                retry += 1
                
            else:
                if "json_validate_failed" in error_msg or "failed to generate json" in error_msg:
                    failed_generation = _extract_failed_generation(str(e))
                    if failed_generation:
                        logging.warning(
                            "⚠️ Groq rejected malformed JSON output (json_validate_failed). "
                            "Recovering the raw generation for local repair instead of discarding it."
                        )
                        raise LLMJsonValidationError(str(e), failed_generation=failed_generation)

                logging.error(f"Unrecoverable Non-429 API exception detected: {e}")
                raise e

    raise TimeoutError("Pipeline execution halted: Max api call retries reached.")










# import time
# import random
# import logging
# from groq import Groq
# import config     # Ensure 'configure' matches your exact file name


# client = Groq(api_key=config.GROQ_API_KEY)

# def call_groq_with_resilience(system_prompt: str, user_prompt: str) -> tuple:
#     """Executes calls incorporating exponential backoff with random uniform jitter."""
#     retry = 0
#     backoff = config.INITIAL_BACKOFF

#     while retry < config.MAX_RETRIES:
#         try:
#             response = client.chat.completions.create(
#                 model=config.MODEL_NAME,
#                 messages=[
#                     {"role": "system", "content": system_prompt},
#                     {"role": "user", "content": user_prompt}
#                 ],
#                 # Uses strict JSON mode switch from config
#                 response_format={"type": "json_object"} if config.STRICT_JSON_MODE else None,
#                 temperature=0.1,
#                 max_tokens=config.MAX_OUTPUT_TOKENS,
#                 timeout=config.REQUEST_TIMEOUT
#             )
#             return response
#         except Exception as e:
#             error_msg = str(e).lower()
#             if "429" in error_msg or "rate limit" in error_msg:
#                 # Calculate sleep incorporating dynamic jitter parameters
#                 sleep_time = (backoff ** retry) + random.uniform(0.1, 0.9)
#                 logging.warning(f"Groq Rate Limit (429) hit. Backing off via Jitter for {round(sleep_time, 2)}s...")
#                 time.sleep(sleep_time)
#                 retry += 1
#             else:
#                 logging.error(f"Unrecoverable Non-429 API exception detected: {e}")
#                 raise e

#     raise TimeoutError("Pipeline execution halted: Max api call retries reached.")




# import logging
# from openai import OpenAI
# import config

# client = OpenAI(
#     base_url=config.OLLAMA_BASE_URL,
#     api_key="ollama"      # Dummy value, required by OpenAI client
# )


# def call_local_llm(system_prompt: str, user_prompt: str):
#     """
#     Executes a local Ollama inference call.
#     No retry logic is required since the model is running locally.
#     """

#     try:
#         response = client.chat.completions.create(
#             model=config.MODEL_NAME,
#             messages=[
#                 {
#                     "role": "system",
#                     "content": system_prompt
#                 },
#                 {
#                     "role": "user",
#                     "content": user_prompt
#                 }
#             ],
#             temperature=0.1,
#             response_format={"type": "json_object"} if config.STRICT_JSON_MODE else None,
#             timeout=config.REQUEST_TIMEOUT
#         )

#         return response

#     except Exception as e:
#         logging.error(f"Local LLM Exception: {e}")
#         raise