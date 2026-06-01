import config
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

print('Loaded env file:', config.env_path)
print('LLM_PROVIDER:', config.LLM_PROVIDER)
print('GOOGLE_API_KEY set:', bool(config.GOOGLE_API_KEY))
print('OPENAI_API_KEY set:', bool(config.OPENAI_API_KEY))
llm = ChatGoogleGenerativeAI(
    model='gpt-4o-mini',
    google_api_key=config.GOOGLE_API_KEY,
    convert_system_message_to_human=True,
)
print('LLM created')
res = llm.invoke([HumanMessage(content='Hello')])
print('Response:', res)
