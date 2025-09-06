import sys
import os
import threading

# Add the project root directory to the Python path to ensure modules can be found.
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from agent import agent_executor
    import config
except ValueError as e: # Catches configuration errors from config.py
    print("\n--- CRITICAL CONFIGURATION ERROR ---", file=sys.stderr)
    print(f"Error: {e}", file=sys.stderr)
    print("\nPlease check your .env file and ensure all required variables are set correctly.", file=sys.stderr)
    print("The application cannot start without valid configuration.", file=sys.stderr)
    sys.exit(1)
except ImportError as e:
    try:
        from voice_input import run_transcription_loop
        from voice_output import speak_text
        from shared_events import interrupt_playback_event
    except ImportError as e:
        print("\n--- VOICE INPUT ERROR ---", file=sys.stderr)
        print(f"Failed to import voice components: {e}", file=sys.stderr)
        print("Please ensure 'pyaudio', 'deepgram-sdk', and 'keyboard' are installed ('pip install -r requirements.txt').", file=sys.stderr)
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

def process_agent_request(prompt: str, chat_history: list) -> tuple[bool, str]:
    """
    Invokes the agent with a prompt and chat history.
    Returns a tuple of (success_status, agent_output). Does not print the output.
    """
    try:
        result = agent_executor.invoke({
            "input": prompt,
            "chat_history": chat_history
        })
        output = result.get('output', '')
        if not output:
            output = "I'm sorry, I couldn't produce an output. Please try rephrasing your request."
        elif "Authentication failed" in output or "invalid credentials" in output:
            return False, output
        return True, output
    except (OpenAIAuthError, AnthropicAuthError):
        # This error occurs if the API key is invalid for OpenAI or Anthropic.
        provider_name = config.LLM_PROVIDER.capitalize()
        error_message = (
            f"\n--- {provider_name} Authentication Error ---\n"
            f"The API key is invalid, expired, or not authorized. "
            f"Please check your {provider_name.upper()}_API_KEY in the .env file."
        )
        print(error_message, file=sys.stderr)
        return False, error_message
    except (OpenAIRateLimitError, AnthropicRateLimitError):
        # This is a specific error for hitting API rate limits for OpenAI or Anthropic.
        provider_name = config.LLM_PROVIDER.capitalize()
        error_message = (
            f"\n--- {provider_name} API Quota Exceeded ---\n"
            f"You have exceeded your current quota for the {provider_name} API. "
            f"Please check your plan and billing details on their website."
        )
        print(error_message, file=sys.stderr)
        return False, error_message
    except DefaultCredentialsError:
        # This error occurs if the API key is present but invalid or not authorized.
        error_message = (
            "\n--- Google Authentication Error ---\n"
            "The API key is invalid, expired, or not authorized for the Gemini API. "
            "Please check your GOOGLE_API_KEY in the .env file.\n"
            "You can get a new key from: https://aistudio.google.com/app/apikey"
        )
        print(error_message, file=sys.stderr)
        return False, error_message
    except ResourceExhausted:
        # This is a specific error for hitting API rate limits.
        error_message = (
            "\n--- API Quota Exceeded ---\n"
            "You have exceeded the request limit for the Google Gemini API, likely on the free tier. "
            "To continue, you need to enable billing for your Google Cloud project.\n\n"
            "1. Visit https://console.cloud.google.com/projectselector2/billing/enable\n"
            "2. Select the project linked to your API key and set up a billing account.\n"
        )
        print(error_message, file=sys.stderr)
        return False, error_message
    except Exception as e:
        error_message = f"\nAn unexpected error occurred: {e}"
        print(error_message, file=sys.stderr)
        return False, error_message

def main():
    """Main function to run the email agent CLI."""
    chat_history = []
    
    # Determine initial input mode from config, but allow it to change during the session.
    input_mode = 'voice' if config.ENABLE_VOICE_INPUT else 'text'

    if input_mode == 'voice':
        print("Email Agent is running in VOICE mode. Say 'text mode' to switch, or 'exit' to quit.")
    else:
        print("Email Agent is running in TEXT mode. Type 'voice mode' to switch, or 'exit' to quit.")

    # --- Initial Prompt ---
    user_input = "Check my unread emails and give me a summary of any new important messages."
    print(f"\nUser: {user_input}")
    print("INFO: Thinking...")
    success, agent_output = process_agent_request(user_input, chat_history)

    if not success:
        print("\nHalting due to a critical error during the initial email check. Please resolve the issue and restart the agent.")
        return

    chat_history.extend([HumanMessage(content=user_input), AIMessage(content=agent_output)])
    print(f"Agent: {agent_output}")

    # --- Main Interaction Loop ---
    while True:
        # --- 1. Get User Input (based on current mode) ---
        if input_mode == 'voice':
            interrupt_playback_event.clear()
            speak_thread = None
            if agent_output: # Don't speak if there was no output (e.g. after switching modes)
                interrupt_playback_event.clear()
                speak_thread = threading.Thread(target=speak_text, args=(agent_output,))
                speak_thread.start()

            # This blocks until user speaks a full utterance
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # This blocks until user speaks a full utterance
                    user_input = run_transcription_loop()
                    break  # Exit the retry loop if successful
                except Exception as e:
                    print(f"Error in voice input (attempt {attempt + 1}/{max_retries}): {e}")
                    if "WebSocketException" in str(e):
                        print("Retrying voice input after a WebSocketException...")
                        time.sleep(2)  # Wait before retrying
                    else:
                        user_input = ""
                        break  # Exit the retry loop for non-recoverable errors

                user_input = "" # Set user_input to empty string so as not to break the loop

            # If the speaking thread is still going, the user must have interrupted.
            # We need to ensure it's stopped and cleaned up.
            if speak_thread and speak_thread.is_alive():
                interrupt_playback_event.set() # Signal the thread to stop
                speak_thread.join() # Wait for it to finish
        else: # input_mode == 'text'
            user_input = input("\nUser: ")

        # --- 2. Handle Commands and Empty Input ---
        if user_input is None: # Happens on Ctrl+C in voice mode
            break
        
        user_input_lower = user_input.strip().lower()

        if not user_input_lower:
            agent_output = "" # Clear agent output to prevent re-speaking on next loop
            continue

        if user_input_lower == 'exit':
            print("Exiting Email Agent. Goodbye!")
            break
        
        if user_input_lower == 'text mode':
            if input_mode == 'voice':
                input_mode = 'text'
                print("\nINFO: Switched to TEXT mode. Type your commands.")
                agent_output = "" # Clear agent output to prevent re-speaking
            else:
                print("INFO: Already in text mode.")
            continue

        if user_input_lower == 'voice mode':
            if not config.ENABLE_VOICE_INPUT:
                print("\nWARNING: Voice mode is disabled in your .env file (ENABLE_VOICE_INPUT=False).")
                agent_output = ""
                continue
            if input_mode == 'text':
                input_mode = 'voice'
                # Provide audio-visual feedback for the mode switch
                agent_output = "Switched to voice mode."
                print(f"\nINFO: {agent_output}")
                speak_text(agent_output)
            else:
                print("INFO: Already in voice mode.")
                agent_output = ""
            continue

        # --- 3. Process Agent Request ---
        print(f"\nUser: {user_input}")
        print("INFO: Thinking...")
        success, agent_output = process_agent_request(user_input, chat_history)

        if success:
            chat_history.extend([HumanMessage(content=user_input), AIMessage(content=agent_output)])
            print(f"Agent: {agent_output}")
        else:
            # Error was already printed by process_agent_request.
            # Clear agent_output so we don't try to speak an old success message.
            agent_output = ""

import time
if __name__ == "__main__":
    main()