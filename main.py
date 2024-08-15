
from langchain_ollama import OllamaLLM

llm = OllamaLLM(model="llama3:8b-instruct-q8_0")

response = llm.generate("Hi")
print(response)