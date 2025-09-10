import sys
import os
import config
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

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


# --- LLM Selection ---
if config.LLM_PROVIDER == "openai":
    llm = ChatOpenAI(model=config.OPENAI_MODEL_NAME, api_key=config.OPENAI_API_KEY, base_url=config.OPENAI_API_BASE)
elif config.LLM_PROVIDER == "google":
    llm = ChatGoogleGenerativeAI(model=config.GEMINI_MODEL_NAME, google_api_key=config.GOOGLE_API_KEY, convert_system_message_to_human=True)
elif config.LLM_PROVIDER == "anthropic":
    llm = ChatAnthropic(model=config.ANTHROPIC_MODEL_NAME, anthropic_api_key=config.ANTHROPIC_API_KEY)


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

# 2. Create the prompt template
prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("placeholder", "{chat_history}"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

# 3. Create the agent and executor
agent = create_tool_calling_agent(llm, all_tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=all_tools, verbose=config.AGENT_VERBOSE, handle_parsing_errors=True)