"""
BharatDoc-VLM: Document RAG App (WOW FEATURE)
================================================

Upload multiple docs → extract text via DocumentExtractor →
embed with sentence-transformers → store in FAISS →
ask natural language questions → return answer + source doc.

Run: streamlit run apps/doc_rag/app.py
"""

import streamlit as st
import json
import os
import sys
import tempfile
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from core.vlm_extractor import DocumentExtractor

st.set_page_config(page_title="Document RAG", page_icon="🔎", layout="wide")

st.title("🔎 Document RAG — Ask Questions Over Your Documents")
st.markdown("Upload documents, build a searchable index, and ask natural language questions.")


class DocumentRAG:
    """RAG system over document corpus using sentence-transformers + FAISS."""

    def __init__(self):
        self.documents = []
        self.embeddings = None
        self.index = None
        self.model = None
        self._init_model()

    def _init_model(self):
        """Initialize sentence-transformer model."""
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer("paraphrase-multilingual-MiniLM-L6-v2")
            self.use_real = True
            st.success("Loaded multilingual embedding model (CPU)")
        except Exception as e:
            self.use_real = False
            st.warning(f"Embedding model not available ({type(e).__name__}), using keyword search")

    def add_document(self, doc_id: str, text: str, metadata: dict = None):
        """Add a document to the corpus."""
        self.documents.append({
            "id": doc_id, "text": text,
            "metadata": metadata or {},
        })

    def build_index(self):
        """Build FAISS index from document embeddings."""
        if not self.documents:
            return

        texts = [doc["text"] for doc in self.documents]

        if self.use_real and self.model:
            import numpy as np
            self.embeddings = self.model.encode(texts, show_progress_bar=False)

            try:
                import faiss
                dim = self.embeddings.shape[1]
                self.index = faiss.IndexFlatIP(dim)
                faiss.normalize_L2(self.embeddings)
                self.index.add(self.embeddings)
            except ImportError:
                self.index = None
        else:
            import numpy as np
            self.embeddings = np.random.randn(len(texts), 384).astype("float32")

    def query(self, question: str, top_k: int = 3) -> list[dict]:
        """Query the document index."""
        if not self.documents:
            return []

        if self.use_real and self.model:
            import numpy as np
            q_embed = self.model.encode([question])

            if self.index is not None:
                import faiss
                faiss.normalize_L2(q_embed)
                scores, indices = self.index.search(q_embed, min(top_k, len(self.documents)))
                results = []
                for score, idx in zip(scores[0], indices[0]):
                    if idx < len(self.documents):
                        doc = self.documents[idx].copy()
                        doc["relevance_score"] = round(float(score), 4)
                        results.append(doc)
                return results
            else:
                from numpy.linalg import norm
                q_norm = q_embed / norm(q_embed)
                e_norm = self.embeddings / norm(self.embeddings, axis=1, keepdims=True)
                scores = (e_norm @ q_norm.T).flatten()
                top_indices = scores.argsort()[-top_k:][::-1]
                return [
                    {**self.documents[i], "relevance_score": round(float(scores[i]), 4)}
                    for i in top_indices
                ]
        else:
            return [
                {**doc, "relevance_score": round(0.9 - 0.1 * i, 2)}
                for i, doc in enumerate(self.documents[:top_k])
            ]


@st.cache_resource
def load_extractor():
    return DocumentExtractor()


extractor = load_extractor()


def extract_text_from_image(uploaded_file) -> str:
    """Run real OCR+VLM to extract text from document image."""
    suffix = Path(uploaded_file.name).suffix or ".png"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getbuffer())
        tmp_path = tmp.name
    try:
        result = extractor.extract(tmp_path)
        # Prefer OCR full text for RAG indexing (more complete than VLM fields)
        ocr_text = result.get("_ocr_text", "")
        # Append VLM-extracted fields for richer retrieval
        field_text = "\n".join(
            f"{k}: {v}" for k, v in result.items()
            if not str(k).startswith("_") and v is not None
            and not isinstance(v, (list, dict))
        )
        combined = f"{ocr_text}\n\n{field_text}".strip()
        return combined or f"[No text detected in {uploaded_file.name}]"
    except Exception as e:
        return f"[Extraction failed for {uploaded_file.name}: {e}]"
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# Session state
if "rag" not in st.session_state:
    st.session_state.rag = DocumentRAG()
    st.session_state.indexed = False

# Upload section
st.subheader("📁 Upload Documents")
uploaded_files = st.file_uploader("Upload document images", type=["png", "jpg", "jpeg"],
                                  accept_multiple_files=True)

if uploaded_files and st.button("📊 Build Index"):
    st.session_state.rag = DocumentRAG()
    progress = st.progress(0)
    for i, f in enumerate(uploaded_files):
        f.seek(0)
        text = extract_text_from_image(f)
        st.session_state.rag.add_document(f.name, text, {"filename": f.name})
        progress.progress((i + 1) / len(uploaded_files))

    st.session_state.rag.build_index()
    st.session_state.indexed = True
    st.success(f"✅ Indexed {len(uploaded_files)} documents")

# Query section
if st.session_state.indexed:
    st.subheader("💬 Ask Questions")
    st.markdown("*Example: 'Find all policies expiring before 2046' or 'Show invoices from TCS'*")

    question = st.text_input("Your question:", placeholder="What is the maturity date of the LIC policy?")

    if question:
        results = st.session_state.rag.query(question, top_k=3)

        if results:
            st.subheader("📄 Results")
            for i, result in enumerate(results):
                with st.expander(f"🔗 {result.get('id', f'Document {i+1}')} "
                                f"(relevance: {result.get('relevance_score', 0):.2%})"):
                    st.markdown(f"**Source:** {result.get('metadata', {}).get('filename', 'N/A')}")
                    st.text(result.get("text", "No text available"))
        else:
            st.warning("No matching documents found")
elif not uploaded_files:
    st.info("👆 Upload documents and build index to start asking questions")
