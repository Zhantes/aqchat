from typing import Dict

from langchain_community.chat_models import ChatOllama

def make_simple_chat_bot(*,
                  model_name: str = "qwen3:32B",
                  ollama_url: str | None = None,
                  messages: Dict[str, str]):
    model = ChatOllama(model=model_name, base_url=ollama_url)
    return model.stream(messages)