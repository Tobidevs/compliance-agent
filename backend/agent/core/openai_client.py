from openai import OpenAI

class OpenAIClient:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    def get_embedding(self, input_text: str, model: str = "text-embedding-3-small") -> list:
        try:
            response = self.client.embeddings.create(input=input_text, model=model)
        except Exception as e:
            print(f"Error getting embedding: {e}")
            return []
        return response.data[0].embedding
    
    def embed_batch(self, input_texts: list[str], model: str = "text-embedding-3-small") -> list[list[float]]:
        try:
            response = self.client.embeddings.create(input=input_texts, model=model)
        except Exception as e:
            print(f"Error getting batch embeddings: {e}")
            return []
        return [item.embedding for item in response.data]