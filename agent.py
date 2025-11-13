import sys
import os
import config
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI  # Keep this as it's used for LLM selection
from langchain_anthropic import ChatAnthropic
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage
from google.api_core.exceptions import NotFound as GoogleModelNotFound

# Add the project root directory to the Python path to ensure modules can be found.
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Tool Imports & Dynamic Assembly ---
# Conditionally import and gather tools based on the .env configuration.
all_tools = []
tool_descriptions = []

if config.ENABLE_EMAIL_APP:
    from email_tools import tools
    all_tools.extend(tools)
    tool_descriptions.append("managing emails (reading, summarizing, and sending)")

if config.ENABLE_ODOO_APP:
    from odoo_tools import tools
    all_tools.extend(tools)
    tool_descriptions.append("planning and creating Odoo environments")

if config.ENABLE_SOCIAL_MEDIA_APP:
    # This assumes the new social_media_tools.py file will be created.
    try:
        from social_media_tools import tools
        all_tools.extend(tools)
        tool_descriptions.append("finding business leads and creating social media content")
    except ImportError:
        print("Warning: Social media tools not found. Please create 'social_media_tools.py'.")


def _openrouter_headers():
    if config.OPENAI_API_BASE and isinstance(config.OPENAI_API_BASE, str) and "openrouter.ai" in config.OPENAI_API_BASE.lower():
        headers = {}
        if config.OPENROUTER_SITE:
            headers["HTTP-Referer"] = config.OPENROUTER_SITE
        if config.OPENROUTER_APP:
            headers["X-Title"] = config.OPENROUTER_APP
        return headers or None
    return None


def _create_llm(provider: str, model_name: str):
    if provider == "openai":
        return ChatOpenAI(
            model=model_name,
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_API_BASE,
            default_headers=_openrouter_headers(),
        )
    if provider == "google":
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=config.GOOGLE_API_KEY,
            convert_system_message_to_human=True,
        )
    if provider == "anthropic":
        return ChatAnthropic(model=model_name, anthropic_api_key=config.ANTHROPIC_API_KEY)
    raise ValueError(f"Unsupported provider: {provider}")


def _preflight_model(llm) -> bool:
    """Attempt a tiny invocation to catch obvious model-not-found issues early.
    Keep it lightweight and provider-agnostic.
    """
    try:
        llm.invoke([HumanMessage(content="ping")])
        return True
    except GoogleModelNotFound:
        return False
    except Exception as e:
        # If the error mentions 'not found' and 'models', treat as not found
        msg = str(e).lower()
        if "not found" in msg and "model" in msg:
            return False
        # Otherwise, don't block startup; defer to runtime
        return True


# --- LLM Selection with optional Gemini auto-fallback ---
if config.LLM_PROVIDER == "google":
    candidates = []
    primary = config.GEMINI_MODEL_NAME
    candidates.append(primary)
    for alt in ("gemini-1.5-flash", "gemini-1.5-pro"):
        if alt != primary and alt not in candidates:
            candidates.append(alt)

    chosen_llm = None
    for name in candidates:
        try:
            llm_candidate = _create_llm("google", name)
            if _preflight_model(llm_candidate):
                chosen_llm = llm_candidate
                if name != primary:
                    print(f"[Agent] Gemini model '{primary}' not available; auto-switched to '{name}'.", file=sys.stderr)
                break
        except Exception:
            continue
    if chosen_llm is None:
        # Provider-level fallback if Gemini models are unavailable
        try_openrouter = bool(
            config.OPENAI_API_BASE
            and isinstance(config.OPENAI_API_BASE, str)
            and "openrouter.ai" in config.OPENAI_API_BASE.lower()
            and (config.OPENAI_API_KEY or getattr(config, "OPENROUTER_API_KEY", None))
        )
        if try_openrouter or config.OPENAI_API_KEY:
            try:
                alt_llm = _create_llm("openai", config.OPENAI_MODEL_NAME)
                if _preflight_model(alt_llm):
                    llm = alt_llm
                    print("[Agent] All Gemini candidates unavailable; fell back to OpenAI/OpenRouter.", file=sys.stderr)
                else:
                    llm = _create_llm("google", primary)
            except Exception:
                llm = _create_llm("google", primary)
        elif config.ANTHROPIC_API_KEY:
            try:
                alt_llm = _create_llm("anthropic", config.ANTHROPIC_MODEL_NAME)
                if _preflight_model(alt_llm):
                    llm = alt_llm
                    print("[Agent] All Gemini candidates unavailable; fell back to Anthropic.", file=sys.stderr)
                else:
                    llm = _create_llm("google", primary)
            except Exception:
                llm = _create_llm("google", primary)
        else:
            llm = _create_llm("google", primary)
    else:
        llm = chosen_llm
elif config.LLM_PROVIDER == "openai":
    # If using OpenRouter, try helpful fallbacks (prefixing and non-mini variants)
    primary = config.OPENAI_MODEL_NAME
    candidates = [primary]
    using_openrouter = bool(
        config.OPENAI_API_BASE
        and isinstance(config.OPENAI_API_BASE, str)
        and "openrouter.ai" in config.OPENAI_API_BASE.lower()
    )
    if using_openrouter:
        # Ensure we try the provider-prefixed variant for OpenRouter
        if "/" not in primary:
            candidates.append(f"openai/{primary}")
        # If a '-mini' model is requested, also try without '-mini'
        def _without_mini(name: str) -> str:
            return name.replace("-mini", "") if name.endswith("-mini") else name
        no_mini_primary = _without_mini(primary)
        if no_mini_primary != primary:
            candidates.append(no_mini_primary)
            if "/" not in no_mini_primary:
                candidates.append(f"openai/{no_mini_primary}")

    chosen_llm = None
    for name in candidates:
        try:
            llm_candidate = _create_llm("openai", name)
            if _preflight_model(llm_candidate):
                chosen_llm = llm_candidate
                if name != primary:
                    print(f"[Agent] OpenRouter model '{primary}' not available; auto-switched to '{name}'.", file=sys.stderr)
                break
        except Exception:
            continue
    llm = chosen_llm or _create_llm("openai", primary)
elif config.LLM_PROVIDER == "anthropic":
    llm = _create_llm("anthropic", config.ANTHROPIC_MODEL_NAME)


# --- Agent Setup ---

# 1. Dynamically create the system prompt
system_prompt_base = "You are a powerful business assistant."
if tool_descriptions:
    system_prompt_tools = " You have access to tools for " + " and ".join(tool_descriptions) + "."
else:
    system_prompt_tools = " You do not have any tools enabled."
# Add a safety instruction for the new workflow
system_prompt_safety = " When finding leads and sending emails, first find the leads, then confirm with the user before sending any emails."
system_prompt = system_prompt_base + system_prompt_tools + system_prompt_safety

# 2. Create the agent graph (LangChain 1.0 API)
graph = create_agent(
    model=llm,
    tools=all_tools,
    system_prompt=system_prompt,
    debug=config.AGENT_VERBOSE,
)


# 3. Backwards-compatible wrapper exposing `.invoke({"input", "chat_history"})`
class AgentExecutorCompat:
    """Compatibility shim so existing code can call `agent_executor.invoke({...})`.

    Expects inputs with keys:
      - "input": user text
      - "chat_history": list[HumanMessage|AIMessage]
    Returns a dict containing at least {"output": str}.
    """

    def __init__(self, graph_compile):
        self._graph = graph_compile

    def invoke(self, inputs: dict):
        user_text = inputs.get("input", "")
        history = inputs.get("chat_history", []) or []
        # Ensure history is a list of Message objects
        messages = list(history)
        if user_text:
            messages.append(HumanMessage(content=user_text))

        # LangChain 1.0 agent graphs take {"messages": [...]} and return a state
        result = self._graph.invoke({"messages": messages})

        # Result should contain a "messages" list ending with an AIMessage
        msgs = result.get("messages", []) if isinstance(result, dict) else []
        output_text = ""
        if msgs:
            # Prefer the last AIMessage content
            ai_msgs = [m for m in msgs if isinstance(m, AIMessage)]
            last_msg = ai_msgs[-1] if ai_msgs else msgs[-1]
            output_text = getattr(last_msg, "content", str(last_msg))

        return {"output": output_text}


agent_executor = AgentExecutorCompat(graph)