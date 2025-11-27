"""Simple TF-IDF based retrieval for local documents."""
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


@dataclass
class DocumentChunk:
    """Represents a document chunk with metadata."""
    id: str
    content: str
    source: str
    score: float = 0.0


class SimpleRetriever:
    """TF-IDF based retrieval over markdown documents."""
    
    def __init__(self, docs_path: str = "docs"):
        self.docs_path = Path(docs_path)
        self.chunks: List[DocumentChunk] = []
        self.vectorizer = TfidfVectorizer(
            max_features=500,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=1
        )
        self.tfidf_matrix = None
        self._load_and_chunk_documents()
    
    def _load_and_chunk_documents(self):
        """Load all markdown files and split into paragraph chunks."""
        if not self.docs_path.exists():
            raise FileNotFoundError(f"Documents path not found: {self.docs_path}")
        
        for md_file in self.docs_path.glob("*.md"):
            content = md_file.read_text(encoding='utf-8')
            file_name = md_file.stem
            
            # Split by paragraphs (double newline or heading)
            paragraphs = re.split(r'\n\s*\n+|\n(?=#)', content)
            paragraphs = [p.strip() for p in paragraphs if p.strip()]
            
            for idx, para in enumerate(paragraphs):
                chunk_id = f"{file_name}::chunk{idx}"
                self.chunks.append(DocumentChunk(
                    id=chunk_id,
                    content=para,
                    source=file_name
                ))
        
        if not self.chunks:
            raise ValueError("No document chunks found!")
        
        # Build TF-IDF matrix
        corpus = [chunk.content for chunk in self.chunks]
        self.tfidf_matrix = self.vectorizer.fit_transform(corpus)
    
    def retrieve(self, query: str, top_k: int = 3) -> List[DocumentChunk]:
        """Retrieve top-k most relevant chunks for the query."""
        if not self.chunks:
            return []
        
        # Transform query
        query_vec = self.vectorizer.transform([query])
        
        # Compute cosine similarity
        similarities = cosine_similarity(query_vec, self.tfidf_matrix)[0]
        
        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        # Create result chunks with scores
        results = []
        for idx in top_indices:
            chunk = self.chunks[idx]
            results.append(DocumentChunk(
                id=chunk.id,
                content=chunk.content,
                source=chunk.source,
                score=float(similarities[idx])
            ))
        
        return results
    
    def get_chunk_by_id(self, chunk_id: str) -> DocumentChunk | None:
        """Get a specific chunk by ID."""
        for chunk in self.chunks:
            if chunk.id == chunk_id:
                return chunk
        return None


def test_retriever():
    """Quick test of the retriever."""
    retriever = SimpleRetriever("docs")
    
    # Test query
    results = retriever.retrieve("return policy for beverages", top_k=2)
    
    print("Test Query: 'return policy for beverages'")
    print("-" * 50)
    for chunk in results:
        print(f"ID: {chunk.id}")
        print(f"Score: {chunk.score:.4f}")
        print(f"Content: {chunk.content[:100]}...")
        print()


if __name__ == "__main__":
    test_retriever()
