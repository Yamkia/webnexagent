import sys
import os
from typing import Optional
import io
from langchain.agents import AgentExecutor

# Add the project root directory to the Python path to ensure modules can be found.
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    # Import the executor directly from the agent module where it's created.
    from agent import agent_executor 
    import config
except (ValueError, ImportError) as e: # Catch both config and import errors
    print("\n--- CRITICAL STARTUP ERROR ---", file=sys.stderr)
    print(f"Error: {e}", file=sys.stderr)
    print("\nThis may be due to a missing dependency, a problem in the agent/tool files, or an invalid .env configuration.", file=sys.stderr)
    sys.exit(1)

from google.auth.exceptions import DefaultCredentialsError
from google.api_core.exceptions import ResourceExhausted
try:
    # Import provider-specific exceptions with aliases to avoid name conflicts.
    from openai import AuthenticationError as OpenAIAuthError, RateLimitError as OpenAIRateLimitError
    from anthropic import AuthenticationError as AnthropicAuthError, RateLimitError as AnthropicRateLimitError
except ImportError:
    # Define dummy exceptions if packages are not installed. This allows the program
    # to run with a single provider without requiring all packages.
    class OpenAIAuthError(Exception): pass
    class OpenAIRateLimitError(Exception): pass
    class AnthropicAuthError(Exception): pass
    class AnthropicRateLimitError(Exception): pass

from langchain_core.messages import HumanMessage, AIMessage

def process_agent_request(prompt: str, chat_history: list) -> tuple[bool, str, Optional[str]]:
    """
    Invokes the agent with a prompt and chat history.
    Returns a tuple of (success_status, agent_output, verbose_log).
    """
    verbose_log = None
    try:
        if config.AGENT_VERBOSE:
            # Redirect stdout and stderr to capture verbose output
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            redirected_output = io.StringIO()
            sys.stdout = redirected_output
            sys.stderr = redirected_output

        result = agent_executor.invoke({
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
    except (OpenAIAuthError, AnthropicAuthError):
        # This error occurs if the API key is invalid for OpenAI or Anthropic.
        provider_name = config.LLM_PROVIDER.capitalize()
        error_message = (
            f"\n--- {provider_name} Authentication Error ---\n"
            f"The API key is invalid, expired, or not authorized. "
            f"Please check your {provider_name.upper()}_API_KEY in the .env file."
        )
        print(error_message, file=sys.stderr) # Still print to server console
        return False, error_message, verbose_log
    except (OpenAIRateLimitError, AnthropicRateLimitError):
        # This is a specific error for hitting API rate limits for OpenAI or Anthropic.
        provider_name = config.LLM_PROVIDER.capitalize()
        error_message = (
            f"\n--- {provider_name} API Quota Exceeded ---\n"
            f"You have exceeded your current quota for the {provider_name} API. "
            f"Please check your plan and billing details on their website."
        )
        print(error_message, file=sys.stderr) # Still print to server console
        return False, error_message, verbose_log
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