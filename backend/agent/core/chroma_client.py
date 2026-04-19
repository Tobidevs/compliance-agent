import chromadb

class ChromaClient:
    def __init__(self, collection_name: str):
        self.client = chromadb.Client()
        self.collection_name = collection_name
        self.collection = self._get_or_create_collection(collection_name)

    def _get_or_create_collection(self, name: str):
        try:
            return self.client.get_collection(name)
        except chromadb.errors.CollectionNotFoundError:
            return self.client.create_collection(name)
    
    def upsert(self, documents: list, embeddings: list, metadata: list = None):
        try:
            self.collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadata
            )
        except Exception as e:
            print(f"Error during upsert: {e}")
            
    def query(self, query_embedding: list, top_k: int = 5):
        try:
            results = self.collection.query(
                query_embeddings=query_embedding,
                n_results=top_k,
            )
            return results
        except Exception as e:
            print(f"Error during query: {e}")
            return None
    def delete(self, ids: list):
        try:
            self.collection.delete(ids=ids)
        except Exception as e:
            print(f"Error during delete: {e}")