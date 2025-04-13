from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import uuid
from services.llm_service import LLMService

class RAGService:
    _instance = None

    @classmethod
    def get_instance(cls):
        """Get or create a RAG instance (singleton pattern)"""
        if cls._instance is None:
            cls._instance = RAGService()
        return cls._instance

    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.index = faiss.IndexIDMap(faiss.IndexFlatL2(384))  # Changed to IndexIDMap for deletions
        self.documents = []  # List of (id, text)
        self.id_to_text = {}

    def add_document(self, text, doc_id=None):
        """Add a document to the RAG index"""
        embedding = self.model.encode([text])[0].astype(np.float32)
        if doc_id is None:
            doc_id = str(uuid.uuid4())
        faiss_id = int(uuid.uuid4().int >> 96)  # Create a 32-bit int ID for FAISS
        self.index.add_with_ids(np.array([embedding]), np.array([faiss_id]))
        self.documents.append((doc_id, text, faiss_id))
        self.id_to_text[doc_id] = (text, faiss_id)
        return doc_id

    def delete_document(self, doc_id):
        """Delete a document by ID from the RAG index"""
        try:
            if doc_id not in self.id_to_text:
                print(f"[RAG] Document ID {doc_id} not found.")
                return

            _, faiss_id = self.id_to_text[doc_id]
            self.index.remove_ids(np.array([faiss_id], dtype=np.int64))

            # Remove from internal stores
            self.documents = [doc for doc in self.documents if doc[0] != doc_id]
            del self.id_to_text[doc_id]

            print(f"[RAG] Successfully deleted doc ID {doc_id}")
        except Exception as e:
            print(f"[RAG] Error deleting document {doc_id}: {e}")

    def search(self, question, top_k=1):
        """Search for documents relevant to a question"""
        if not self.documents:
            return []
        query_embedding = self.model.encode([question])[0].astype(np.float32)
        D, I = self.index.search(np.array([query_embedding]), top_k)
        results = []
        for idx in I[0]:
            for doc_id, doc_text, faiss_id in self.documents:
                if faiss_id == idx:
                    results.append({
                        "id": doc_id,
                        "text": doc_text
                    })
                    break
        return results

    def query(self, question, top_k=3):
        """Query the RAG system with a question and get LLM-enhanced answers"""
        results = self.search(question, top_k=top_k)

        if not results:
            return "I don't have enough information to answer that question."

        # Concatenate retrieved documents
        context = "\n\n".join([doc["text"] for doc in results])

        # Create prompt for LLM
        prompt = f"""
        You are a helpful career assistant. Answer the following question based only on the information provided:

        Context:
        {context}

        Question: {question}

        Answer:
        """

        # Get response from LLM
        response = LLMService.invoke(prompt)
        return response.content

    def query_similar_cvs(self, cv_text, top_k=3):
        """Find CVs similar to the provided CV text"""
        return self.search(cv_text, top_k=top_k)
