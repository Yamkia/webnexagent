import config
from langchain_google_genai import ChatGoogleGenerativeAI
print('config provider', config.LLM_PROVIDER)
print('config GOOGLE_API_KEY set:', bool(config.GOOGLE_API_KEY))
llm = ChatGoogleGenerativeAI(model='gpt-4o-mini', google_api_key=config.GOOGLE_API_KEY, convert_system_message_to_human=True)
print('llm created')
resp = llm.generate([{'type': 'human', 'text': 'Hello'}])
print('response', resp)
