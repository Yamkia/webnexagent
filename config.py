import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the same directory as this config file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# --- API Keys ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # For OpenAI models
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE") # For custom OpenAI-compatible endpoints like OpenRouter
# OpenRouter convenience variables (optional): if using OpenRouter, you can set these
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_SITE = os.getenv("OPENROUTER_SITE")   # Will be used as HTTP-Referer header (recommended by OpenRouter)
OPENROUTER_APP = os.getenv("OPENROUTER_APP")     # Will be used as X-Title header (recommended by OpenRouter)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # For Google Gemini models
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY") # For Anthropic Claude models
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY") # For Deepgram voice transcription

# Debug: Print loaded API keys (for troubleshooting only)
print(f"[DEBUG] .env path: {env_path} (exists={env_path.exists()})")
print(f"[DEBUG] Loaded OPENAI_API_KEY: {OPENAI_API_KEY}")
print(f"[DEBUG] Loaded GOOGLE_API_KEY: {GOOGLE_API_KEY}")
print(f"[DEBUG] Loaded LLM_PROVIDER: {os.getenv('LLM_PROVIDER')}")

# --- Model Settings ---
# Provider can be: "openai", "google", "anthropic", or "auto" (auto-detect based on available keys)
LLM_PROVIDER_RAW = os.getenv("LLM_PROVIDER", "auto").lower()
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash-latest")
# Normalize Gemini alias: remove "-latest" if library/API rejects it
if GEMINI_MODEL_NAME.endswith("-latest"):
    GEMINI_MODEL_NAME = GEMINI_MODEL_NAME.replace("-latest", "")
ANTHROPIC_MODEL_NAME = os.getenv("ANTHROPIC_MODEL_NAME", "claude-3-5-sonnet-20240620")

# Auto-detect provider if requested. Allow explicitly disabling the agent by setting LLM_PROVIDER to 'none' or 'disabled'.
if LLM_PROVIDER_RAW in ("", "auto"):
    if OPENAI_API_BASE and isinstance(OPENAI_API_BASE, str) and "openrouter.ai" in OPENAI_API_BASE.lower() and (OPENAI_API_KEY or OPENROUTER_API_KEY):
        LLM_PROVIDER = "openai"
    elif OPENAI_API_KEY:
        LLM_PROVIDER = "openai"
    elif GOOGLE_API_KEY:
        LLM_PROVIDER = "google"
    elif ANTHROPIC_API_KEY:
        LLM_PROVIDER = "anthropic"
    else:
        # No provider keys found: do not force a provider. Agent will be disabled.
        LLM_PROVIDER = None
elif LLM_PROVIDER_RAW in ("none", "disabled"):
    LLM_PROVIDER = None
else:
    LLM_PROVIDER = LLM_PROVIDER_RAW

# --- Agent Settings ---
AGENT_VERBOSE = os.getenv("AGENT_VERBOSE", "False").lower() in ('true', '1', 't')

# Convenience flag for app code to check whether an LLM provider is configured
AGENT_ENABLED = LLM_PROVIDER is not None


# --- App Visibility Settings ---
# Control which applications are enabled and visible in the UI.
ENABLE_EMAIL_APP = os.getenv("ENABLE_EMAIL_APP", "True").lower() in ('true', '1', 't')
ENABLE_ODOO_APP = os.getenv("ENABLE_ODOO_APP", "True").lower() in ('true', '1', 't')
ENABLE_SOCIAL_MEDIA_APP = os.getenv("ENABLE_SOCIAL_MEDIA_APP", "False").lower() in ('true', '1', 't')
ENABLE_TRAFFIC_APP = os.getenv("ENABLE_TRAFFIC_APP", "True").lower() in ('true', '1', 't')
ENABLE_BRAND_MANAGER_APP = os.getenv("ENABLE_BRAND_MANAGER_APP", "True").lower() in ('true', '1', 't')
ENABLE_WEBSITE_HELPER_APP = os.getenv("ENABLE_WEBSITE_HELPER_APP", "True").lower() in ('true', '1', 't')

# --- Input Settings ---
ENABLE_VOICE_INPUT = os.getenv("ENABLE_VOICE_INPUT", "False").lower() in ('true', '1', 't')

# --- Email Credentials ---
IMAP_SERVER = os.getenv("IMAP_SERVER")
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = os.getenv("SMTP_PORT", "465") # Default to 465, common for SMTP_SSL
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# --- Configuration Validation ---
# We centralize all critical configuration checks here to fail fast.

# If user is using OpenRouter via the OpenAI-compatible API, allow OPENROUTER_API_KEY as a fallback
if OPENAI_API_BASE and isinstance(OPENAI_API_BASE, str) and "openrouter.ai" in OPENAI_API_BASE.lower():
    # Treat placeholder OPENAI_API_KEY as unset so OPENROUTER_API_KEY can be used as a fallback
    if (not OPENAI_API_KEY or (isinstance(OPENAI_API_KEY, str) and 'your-openai-api-key-here' in OPENAI_API_KEY)) and OPENROUTER_API_KEY:
        OPENAI_API_KEY = OPENROUTER_API_KEY

if LLM_PROVIDER is None:
    # Agent explicitly disabled or no provider keys found; skip provider validation.
    pass
elif LLM_PROVIDER == "openai":
    if OPENAI_API_BASE and isinstance(OPENAI_API_BASE, str) and "openrouter.ai" in OPENAI_API_BASE.lower():
        if not OPENAI_API_KEY:
            raise ValueError(
                "LLM_PROVIDER is 'openai' with OpenRouter base URL, but no API key was provided. "
                "Set either OPENAI_API_KEY or OPENROUTER_API_KEY in your .env file."
            )
    else:
        if not OPENAI_API_KEY or "your-openai-api-key-here" in OPENAI_API_KEY:
            raise ValueError(
                "LLM_PROVIDER is set to 'openai', but OPENAI_API_KEY is missing or is a placeholder in the .env file. "
                "Please add your OpenAI API key."
            )
elif LLM_PROVIDER == "google":
    if not GOOGLE_API_KEY or "your-google-api-key-here" in GOOGLE_API_KEY:
        raise ValueError(
            "LLM_PROVIDER is set to 'google', but GOOGLE_API_KEY is missing or is a placeholder in the .env file. "
            "Please get a key from https://aistudio.google.com/app/apikey and add it."
        )
elif LLM_PROVIDER == "anthropic":
    if not ANTHROPIC_API_KEY or "your-anthropic-api-key-here" in ANTHROPIC_API_KEY:
        raise ValueError(
            "LLM_PROVIDER is set to 'anthropic', but ANTHROPIC_API_KEY is missing or is a placeholder in the .env file. "
            "Please add your Anthropic API key."
        )
else:
    raise ValueError(f"Invalid LLM_PROVIDER '{LLM_PROVIDER}' after auto-detection. Must resolve to 'openai', 'google', or 'anthropic'.")

# 2. Check for Voice Input Dependencies
if ENABLE_VOICE_INPUT and (not DEEPGRAM_API_KEY or "your-deepgram-api-key-here" in DEEPGRAM_API_KEY):
    raise ValueError(
        "ENABLE_VOICE_INPUT is set to 'true', but DEEPGRAM_API_KEY is missing or is a placeholder in the .env file. "
        "Please add your Deepgram API key."
    )

# 3. Check for Email Credentials
if ENABLE_EMAIL_APP:
    if not all([IMAP_SERVER, SMTP_SERVER, EMAIL_USER, EMAIL_PASSWORD]) or \
       EMAIL_USER == "your-email@example.com" or \
       EMAIL_PASSWORD == "your-email-password" or \
       IMAP_SERVER == "imap.example.com" or \
       SMTP_SERVER == "smtp.example.com":
        raise ValueError(
            "ENABLE_EMAIL_APP is true, but email credentials (IMAP_SERVER, SMTP_SERVER, EMAIL_USER, EMAIL_PASSWORD) are missing or placeholders in the .env file. "
            "Please add your email details or set ENABLE_EMAIL_APP to false."
        )

# 4. Validate SMTP_PORT
try:
    SMTP_PORT = int(SMTP_PORT)
except ValueError:
    raise ValueError("SMTP_PORT in .env file must be a valid number.")

# --- Optional Odoo/Postgres Settings (for local environments) ---
# These are used by the Odoo helper routes to create/run local Odoo databases.
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
ODOO_DB_USER = os.getenv("ODOO_DB_USER", "odoo")
ODOO_DB_PASSWORD = os.getenv("ODOO_DB_PASSWORD", "odoo")