"""
Query vector store for relevant business rules.
"""

import logging
from typing import List, Dict
import httpx
import chromadb
from chromadb.config import Settings
from src.config.settings import settings as app_settings

logger = logging.getLogger(__name__)


def get_ollama_embedding(text: str, model: str) -> List[float]:
    """
    Get embedding from Ollama API.
    
    Args:
        text: Text to embed
        model: Ollama embedding model name
        
    Returns:
        Embedding vector as list of floats
    """
    url = f"{app_settings.OLLAMA_URL}/api/embeddings"
    
    payload = {
        "model": model,
        "prompt": text
    }
    
    response = httpx.post(url, json=payload, timeout=30)
    response.raise_for_status()
    
    result = response.json()
    return result["embedding"]


class RulesRetriever:
    """Retrieves relevant business rules using RAG."""
    
    def __init__(self, collection_name: str = "business_policies"):
        self.collection = None
        self.collection_name = collection_name
        self._initialize()
    
    def _initialize(self):
        """Initialize vector store connection."""
        try:
            # Note: Using Ollama for embeddings - no model loading needed
            logger.info(f"Using Ollama embedding model: {app_settings.EMBEDDING_MODEL}")
            
            # Connect to ChromaDB
            client = chromadb.PersistentClient(
                path=str(app_settings.VECTORSTORE_DIR),
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Try to get collection - try multiple possible names for backward compatibility
            collection_names = [self.collection_name, "business_rules", "business_policies"]
            
            for name in collection_names:
                try:
                    self.collection = client.get_collection(name)
                    self.collection_name = name
                    logger.info(f"Connected to collection: {name}")
                    break
                except:
                    continue
            
            if not self.collection:
                raise Exception(f"No vector store collection found. Run: python src/agents/rules_rag/build_vectorstore.py")
            
            # Log collection info
            count = self.collection.count()
            logger.info(f"Rules retriever initialized successfully ({count} documents)")
            
        except Exception as e:
            logger.error(f"Failed to initialize rules retriever: {str(e)}", exc_info=True)
            raise Exception(f"RAG initialization failed: {str(e)}")
    
    def retrieve_rules(self, query: str, top_k: int = None) -> List[str]:
        """
        Retrieve relevant business rules for a query.
        
        Args:
            query: Query string describing the validation context
            top_k: Number of rules to retrieve (default from settings)
            
        Returns:
            List of relevant rule texts
        """
        try:
            if top_k is None:
                top_k = app_settings.TOP_K_RULES
            
            # Generate query embedding using Ollama
            query_embedding = get_ollama_embedding(query, app_settings.EMBEDDING_MODEL)
            
            # Query collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
            
            # Extract documents
            documents = results.get('documents', [[]])[0]
            
            logger.info(f"Retrieved {len(documents)} relevant rules for query")
            logger.debug(f"Query: {query[:100]}...")
            
            return documents
            
        except Exception as e:
            logger.error(f"Rule retrieval failed: {str(e)}", exc_info=True)
            # Return empty list as fallback
            return []
    
    def retrieve_rules_with_scores(self, query: str, top_k: int = None) -> List[Dict]:
        """
        Retrieve rules with relevance scores.
        
        Args:
            query: Query string
            top_k: Number of rules to retrieve
            
        Returns:
            List of dicts with 'text' and 'score' keys
        """
        try:
            if top_k is None:
                top_k = app_settings.TOP_K_RULES
            
            # Generate query embedding using Ollama
            query_embedding = get_ollama_embedding(query, app_settings.EMBEDDING_MODEL)
            
            # Query collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
            
            # Extract documents and distances
            documents = results.get('documents', [[]])[0]
            distances = results.get('distances', [[]])[0]
            
            # Convert distances to similarity scores (lower distance = higher similarity)
            rules_with_scores = []
            for doc, dist in zip(documents, distances):
                # Convert distance to similarity score (0-1)
                score = 1.0 / (1.0 + dist)
                rules_with_scores.append({
                    'text': doc,
                    'score': score
                })
            
            logger.info(f"Retrieved {len(rules_with_scores)} rules with scores")
            
            return rules_with_scores
            
        except Exception as e:
            logger.error(f"Rule retrieval with scores failed: {str(e)}", exc_info=True)
            return []
    
    def get_all_rules(self) -> List[str]:
        """
        Get all rules from vector store (for debugging).
        
        Returns:
            List of all rule texts
        """
        try:
            # Get all documents
            results = self.collection.get()
            documents = results.get('documents', [])
            
            logger.info(f"Retrieved all {len(documents)} rules")
            
            return documents
            
        except Exception as e:
            logger.error(f"Failed to get all rules: {str(e)}", exc_info=True)
            return []


# Singleton instance
rules_retriever = RulesRetriever()
