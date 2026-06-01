import config
import pkg_resources

print('env_path', getattr(config, 'env_path', 'N/A'))
print('LLM_PROVIDER_RAW', config.LLM_PROVIDER_RAW)
print('LLM_PROVIDER', config.LLM_PROVIDER)
print('GOOGLE_API_KEY set', bool(config.GOOGLE_API_KEY))
print('OPENAI_API_KEY set', bool(config.OPENAI_API_KEY))
print('OPENAI_API_BASE', config.OPENAI_API_BASE)
print('langchain-google-genai', pkg_resources.get_distribution('langchain-google-genai').version)
