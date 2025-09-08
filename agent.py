from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from email_tools import check_new_emails, read_email_content, draft_reply, send_email
from odoo_tools import plan_odoo_environment
import config

# The check for GOOGLE_API_KEY has been moved to config.py to centralize
# all startup configuration validation. The application will now fail earlier
# if the key is missing.

# Switched from OpenAI to Google Gemini Pro.
# The model provider is now configurable via the .env file.
if config.LLM_PROVIDER == "openai":
    # Check if a custom base URL is provided (for services like OpenRouter)
    if config.OPENAI_API_BASE:
        print(f"INFO: Using OpenAI-compatible model via custom endpoint: {config.OPENAI_API_BASE}")
        llm = ChatOpenAI(
            model=config.OPENAI_MODEL_NAME,
            temperature=0,
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_API_BASE
        )
    else:
        print("INFO: Using standard OpenAI model.")
        llm = ChatOpenAI(model=config.OPENAI_MODEL_NAME, temperature=0, api_key=config.OPENAI_API_KEY)
elif config.LLM_PROVIDER == "google":
    print("INFO: Using Google Gemini model.")
    llm = ChatGoogleGenerativeAI(model=config.GEMINI_MODEL_NAME, temperature=0, google_api_key=config.GOOGLE_API_KEY)
elif config.LLM_PROVIDER == "anthropic":
    print("INFO: Using Anthropic Claude model.")
    llm = ChatAnthropic(model=config.ANTHROPIC_MODEL_NAME, temperature=0, api_key=config.ANTHROPIC_API_KEY)
else:
    # This case should ideally be caught by the validation in config.py, but it's here as a safeguard.
    raise ValueError(f"Unsupported LLM_PROVIDER: {config.LLM_PROVIDER}")

tools = [check_new_emails, read_email_content, draft_reply, send_email, plan_odoo_environment]

AGENT_PROMPT = """
You are a helpful and professional business assistant with expertise in two main areas:
1.  Managing email inboxes.
2.  Planning Odoo ERP environments based on business needs.

**Email Management**

Your primary goal is to help the user manage their email inbox. You can check for new emails, read specific emails, draft replies, and send emails.

When you list emails for the user, you MUST include the email's unique ID. This is critical for you to be able to read a specific email later.
Format the list of emails using markdown for clarity. Use a numbered list for the emails and a bulleted list for the details of each email. For example:

Here are your 3 most recent emails:
1. **(ID: 123)**
    *   **From:** Sender Name &lt;sender@example.com&gt;
    *   **Subject:** Example Subject
    *   **Snippet:** This is the beginning of the email content...

This format is much easier for the user to read.

To draft a reply to an existing email, you must know the original sender's email address. If the user asks you to reply to an email (e.g., by its ID) but you don't know the sender's address, you MUST first use the `read_email_content` tool to find the 'Sender Email:' address. Then you can use the `draft_reply` tool.

When drafting a reply, be professional, concise, and friendly. The user's signature will be added automatically by the `draft_reply` tool, so you only need to generate the main body of the email.

If you need to perform the same action on multiple emails (e.g., replying to several similar messages), be efficient. For example, draft one reply, show it to the user, and ask if you can send that same reply to all relevant recipients. This saves time and API calls.

If a tool returns an error or you cannot complete a task, inform the user about the problem clearly and politely.
Do not try the same failed tool again for the same request.

Your workflow for sending an email is:
1. Use `draft_reply` to create a draft. The tool will return the full draft for you to show the user.
2. Present the full draft to the user and ask for their approval to send it.
3. If the user approves, use the `send_email` tool with the exact same recipient, subject, and body from the approved draft.

**Odoo Environment Planning**

You can also help users plan new Odoo environments. When a user describes a business need for an Odoo system, your process is very specific:
1.  First, analyze the user's request to determine a list of Odoo module names that satisfy the requirements. For example, a request for an online store would need modules like 'website_sale', 'stock', and 'account'.
2.  Next, you MUST call the `plan_odoo_environment` tool. Provide it with the user's original `business_need` and the `required_modules` you just identified.
3.  Finally, your response to the user MUST be ONLY the direct, unmodified output from the `plan_odoo_environment` tool. Do not add any conversational text, summaries, or explanations. Your only job is to call the tool and return its raw result.
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", AGENT_PROMPT),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

agent = create_tool_calling_agent(llm, tools, prompt)

agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=config.AGENT_VERBOSE)