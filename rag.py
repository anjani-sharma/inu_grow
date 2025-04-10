from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import uuid

class RAG:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.index = faiss.IndexFlatL2(384)
        self.documents = []  # List of (id, text)
        self.id_to_text = {}

    def add_document(self, text, doc_id=None):
        embedding = self.model.encode([text])[0]
        self.index.add(np.array([embedding]))
        if doc_id is None:
            doc_id = str(uuid.uuid4())
        self.documents.append((doc_id, text))
        self.id_to_text[doc_id] = text
        return doc_id

    def query(self, question, top_k=1):
        if not self.documents:
            return "No documents available to query."
        query_embedding = self.model.encode([question])[0]
        D, I = self.index.search(np.array([query_embedding]), top_k)
        results = []
        for idx in I[0]:
            if 0 <= idx < len(self.documents):
                doc_id, doc_text = self.documents[idx]
                results.append({
                    "id": doc_id,
                    "text": doc_text
                })
        return results

    def query_similar_cvs(self, cv_text, top_k=3):
        return self.query(cv_text, top_k=top_k)