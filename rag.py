from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

class RAG:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.index = faiss.IndexFlatL2(384)  # 384 is the embedding size for this model
        self.documents = []

    def add_document(self, text):
        embedding = self.model.encode([text])[0]
        self.index.add(np.array([embedding]))
        self.documents.append(text)

    def query(self, question):
        if not self.documents:
            return "No documents available to query."
        query_embedding = self.model.encode([question])[0]
        D, I = self.index.search(np.array([query_embedding]), 1)
        return self.documents[I[0][0]]