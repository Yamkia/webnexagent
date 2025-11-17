import sys
import os
from typing import Optional
import io
# Add the project root directory to the Python path to ensure modules can be found.
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    import config
except (ValueError, ImportError) as e:
    print("\n--- CRITICAL STARTUP ERROR ---", file=sys.stderr)
    print(f"Error: {e}", file=sys.stderr)
    print("\nThis may be due to a missing dependency, a problem in the agent/tool files, or an invalid .env configuration.", file=sys.stderr)
    raise

# Lazy-load the agent to avoid heavy imports at startup
_agent_executor = None

from google.auth.exceptions import DefaultCredentialsError
from google.api_core.exceptions import ResourceExhausted
# Avoid importing heavyweight SDKs (openai/anthropic) at startup; we'll detect by name at runtime.
class OpenAIAuthError(Exception):
    pass

class OpenAIRateLimitError(Exception):
    pass

class AnthropicAuthError(Exception):
    pass

class AnthropicRateLimitError(Exception):
    pass

from langchain_core.messages import HumanMessage, AIMessage

def process_agent_request(prompt: str, chat_history: list) -> tuple[bool, str, Optional[str]]:
    """
    Invokes the agent with a prompt and chat history.
    Returns a tuple of (success_status, agent_output, verbose_log).
    """
    verbose_log = None
    try:
        global _agent_executor
        if _agent_executor is None:
            from agent import agent_executor as _ae
            _agent_executor = _ae
        if config.AGENT_VERBOSE:
            # Redirect stdout and stderr to capture verbose output
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            redirected_output = io.StringIO()
            sys.stdout = redirected_output
            sys.stderr = redirected_output

        result = _agent_executor.invoke({
            "input": prompt,
            "chat_history": chat_history
        })
        output = result.get('output', '')

        if config.AGENT_VERBOSE:
            sys.stdout = old_stdout # Restore original stdout
            sys.stderr = old_stderr # Restore original stderr
            verbose_log = redirected_output.getvalue()
            # Optionally, print to the server console as well for local debugging
            print("\n--- AGENT VERBOSE LOG (captured) ---", file=sys.stderr)
            print(verbose_log, file=sys.stderr)
            print("------------------------------------", file=sys.stderr)

        if not output:
            output = "I'm sorry, I couldn't produce an output. Please try rephrasing your request."
        elif "Authentication failed" in output or "invalid credentials" in output:
            return False, output, verbose_log
        return True, output, verbose_log
    except Exception as e:
        # Map provider-specific errors without importing heavy SDKs at startup
        ename = e.__class__.__name__
        emod = getattr(e.__class__, "__module__", "")
        if ("openai" in emod and ename in ("AuthenticationError",)) or (
            "anthropic" in emod and ename in ("AuthenticationError",)
        ):
            provider_name = config.LLM_PROVIDER.capitalize()
            error_message = (
                f"\n--- {provider_name} Authentication Error ---\n"
                f"The API key is invalid, expired, or not authorized. "
                f"Please check your {provider_name.upper()}_API_KEY in the .env file."
            )
            print(error_message, file=sys.stderr)
            return False, error_message, verbose_log
        if ("openai" in emod and ename in ("RateLimitError",)) or (
            "anthropic" in emod and ename in ("RateLimitError",)
        ):
            provider_name = config.LLM_PROVIDER.capitalize()
            error_message = (
                f"\n--- {provider_name} API Quota Exceeded ---\n"
                f"You have exceeded your current quota for the {provider_name} API. "
                f"Please check your plan and billing details on their website."
            )
            print(error_message, file=sys.stderr)
            return False, error_message, verbose_log
        raise
    except DefaultCredentialsError:
        # This error occurs if the API key is present but invalid or not authorized.
        error_message = (
            "\n--- Google Authentication Error ---\n"
            "The API key is invalid, expired, or not authorized for the Gemini API. "
            "Please check your GOOGLE_API_KEY in the .env file.\n"
            "You can get a new key from: https://aistudio.google.com/app/apikey"
        ) 
        print(error_message, file=sys.stderr) # Still print to server console
        return False, error_message, verbose_log
    except ResourceExhausted:
        # This is a specific error for hitting API rate limits.
        error_message = (
            "\n--- API Quota Exceeded ---\n"
            "You have exceeded the request limit for the Google Gemini API, likely on the free tier. "
            "To continue, you need to enable billing for your Google Cloud project.\n\n"
            "1. Visit https://console.cloud.google.com/projectselector2/billing/enable\n"
            "2. Select the project linked to your API key and set up a billing account.\n"
        ) 
        print(error_message, file=sys.stderr) # Still print to server console
        return False, error_message, verbose_log
    except Exception as e:
        error_message = f"\nAn unexpected error occurred: {e}"
        print(error_message, file=sys.stderr) # Still print to server console
        return False, error_message, verbose_log