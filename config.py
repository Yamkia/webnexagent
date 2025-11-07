import os
from dotenv import load_dotenv

load_dotenv()

# --- API Keys ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # For OpenAI models
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE") # For custom OpenAI-compatible endpoints like OpenRouter
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # For Google Gemini models
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY") # For Anthropic Claude models
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY") # For Deepgram voice transcription

# --- Model Settings ---
# Set the provider for the large language model. Can be "openai", "google", or "anthropic".
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "google").lower()
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash-latest")
ANTHROPIC_MODEL_NAME = os.getenv("ANTHROPIC_MODEL_NAME", "claude-3-5-sonnet-20240620")

# --- Agent Settings ---
AGENT_VERBOSE = os.getenv("AGENT_VERBOSE", "False").lower() in ('true', '1', 't')

# --- App Visibility Settings ---
# Control which applications are enabled and visible in the UI.
ENABLE_EMAIL_APP = os.getenv("ENABLE_EMAIL_APP", "True").lower() in ('true', '1', 't')
ENABLE_ODOO_APP = os.getenv("ENABLE_ODOO_APP", "True").lower() in ('true', '1', 't')
ENABLE_SOCIAL_MEDIA_APP = os.getenv("ENABLE_SOCIAL_MEDIA_APP", "True").lower() in ('true', '1', 't')
ENABLE_TRAFFIC_APP = os.getenv("ENABLE_TRAFFIC_APP", "True").lower() in ('true', '1', 't')
ENABLE_BRAND_MANAGER_APP = os.getenv("ENABLE_BRAND_MANAGER_APP", "True").lower() in ('true', '1', 't')

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

if LLM_PROVIDER == "openai":
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
    raise ValueError(f"Invalid LLM_PROVIDER '{LLM_PROVIDER}' in .env file. Must be 'openai', 'google', or 'anthropic'.")

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