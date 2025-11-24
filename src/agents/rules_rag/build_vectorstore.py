"""
Build vector store from business policies/rules.
This script creates embeddings and stores them for RAG retrieval.
Supports loading from sample_business_polices.txt or any text file.
"""

import logging
import sys
from pathlib import Path
from typing import List, Optional
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


def load_rules_text(file_path: Optional[Path] = None) -> str:
    """
    Load business rules from text file.
    
    Args:
        file_path: Optional path to rules file. If None, uses config default.
        
    Returns:
        Text content of the rules file
    """
    try:
        target_file = file_path or app_settings.RULES_FILE
        
        if not target_file.exists():
            raise FileNotFoundError(f"Rules file not found: {target_file}")
        
        with open(target_file, 'r', encoding='utf-8') as f:
            text = f.read()
        
        if not text.strip():
            raise ValueError("Rules file is empty")
        
        logger.info(f"Loaded {len(text)} characters from {target_file.name}")
        logger.info(f"File location: {target_file}")
        
        return text
        
    except Exception as e:
        logger.error(f"Failed to load rules: {str(e)}")
        raise


def chunk_text(text: str, chunk_size: Optional[int] = None, overlap: Optional[int] = None) -> List[str]:
    """
    Split text into chunks for embedding with intelligent section handling.
    
    Args:
        text: Full text to chunk
        chunk_size: Target size per chunk (characters). Uses config default if None.
        overlap: Overlap between chunks. Uses config default if None.
        
    Returns:
        List of text chunks
    """
    if chunk_size is None:
        chunk_size = app_settings.CHUNK_SIZE
    if overlap is None:
        overlap = app_settings.CHUNK_OVERLAP
    
    logger.info(f"Chunking with size={chunk_size}, overlap={overlap}")
    
    # Split by sections (double newline for paragraphs/sections)
    sections = text.split('\n\n')
    
    chunks = []
    current_chunk = ""
    
    for section in sections:
        section = section.strip()
        if not section:
            continue
        
        # If section alone is too large, split it further
        if len(section) > chunk_size * 1.5:
            # Split by sentences or newlines
            subsections = section.split('\n')
            for subsection in subsections:
                subsection = subsection.strip()
                if not subsection:
                    continue
                    
                if len(current_chunk) + len(subsection) > chunk_size and current_chunk:
                    chunks.append(current_chunk.strip())
                    # Keep overlap
                    current_chunk = current_chunk[-overlap:] + "\n" + subsection
                else:
                    current_chunk = current_chunk + "\n" + subsection if current_chunk else subsection
        else:
            # Normal section processing
            if len(current_chunk) + len(section) > chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                # Keep overlap from previous chunk
                current_chunk = current_chunk[-overlap:] + "\n\n" + section
            else:
                if current_chunk:
                    current_chunk += "\n\n" + section
                else:
                    current_chunk = section
    
    # Add final chunk
    if current_chunk and current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    # Log chunk statistics
    logger.info(f"Created {len(chunks)} chunks")
    if chunks:
        avg_length = sum(len(c) for c in chunks) / len(chunks)
        logger.info(f"Average chunk length: {avg_length:.0f} characters")
        logger.info(f"Chunk sizes range: {min(len(c) for c in chunks)} - {max(len(c) for c in chunks)}")
    
    return chunks


def build_vectorstore(file_path: Optional[Path] = None, collection_name: str = "business_policies"):
    """
    Build and save vector store from business policies.
    
    Args:
        file_path: Optional path to policies file. Uses config default if None.
        collection_name: Name for the ChromaDB collection
        
    Returns:
        True if successful
    """
    try:
        # Load rules/policies
        rules_text = load_rules_text(file_path)
        
        # Chunk text
        chunks = chunk_text(rules_text)
        
        if not chunks:
            raise Exception("No chunks created from rules text")
        
        # Generate embeddings using Ollama
        logger.info(f"Using Ollama embedding model: {app_settings.EMBEDDING_MODEL}")
        logger.info(f"Generating embeddings for {len(chunks)} chunks...")
        
        embeddings = []
        for i, chunk in enumerate(chunks):
            if i % 10 == 0:
                logger.info(f"  Processing chunk {i+1}/{len(chunks)}...")
            
            try:
                embedding = get_ollama_embedding(chunk, app_settings.EMBEDDING_MODEL)
                embeddings.append(embedding)
            except Exception as e:
                logger.error(f"Failed to generate embedding for chunk {i}: {str(e)}")
                raise
        
        logger.info(f"Generated {len(embeddings)} embeddings (dimension: {len(embeddings[0])})")
        
        # Initialize ChromaDB
        logger.info(f"Initializing ChromaDB at {app_settings.VECTORSTORE_DIR}")
        
        # Ensure directory exists
        app_settings.VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)
        
        client = chromadb.PersistentClient(
            path=str(app_settings.VECTORSTORE_DIR),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Delete existing collection if it exists
        try:
            client.delete_collection(collection_name)
            logger.info(f"Deleted existing collection: {collection_name}")
        except:
            logger.info(f"No existing collection to delete: {collection_name}")
        
        # Create new collection with metadata
        collection = client.create_collection(
            name=collection_name,
            metadata={
                "description": "Travel invoice validation business policies and rules",
                "source_file": str(file_path or app_settings.RULES_FILE),
                "chunk_count": len(chunks),
                "embedding_model": app_settings.EMBEDDING_MODEL
            }
        )
        
        logger.info(f"Created collection: {collection_name}")
        
        # Add documents to collection in batches
        logger.info("Adding documents to collection...")
        
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            batch_end = min(i + batch_size, len(chunks))
            
            batch_ids = [f"policy_{j}" for j in range(i, batch_end)]
            batch_embeddings = embeddings[i:batch_end]  # Already lists from Ollama
            batch_documents = chunks[i:batch_end]
            batch_metadata = [{"chunk_index": j, "chunk_length": len(chunks[j])} for j in range(i, batch_end)]
            
            collection.add(
                embeddings=batch_embeddings,
                documents=batch_documents,
                ids=batch_ids,
                metadatas=batch_metadata
            )
            
            logger.info(f"Added batch {i//batch_size + 1}: chunks {i} to {batch_end-1}")
        
        # Verify collection
        count = collection.count()
        logger.info(f"✓ Successfully built vector store with {count} documents")
        logger.info(f"✓ Vector store saved to: {app_settings.VECTORSTORE_DIR}")
        
        # Test retrieval
        logger.info("Testing retrieval...")
        test_results = collection.query(
            query_embeddings=[embeddings[0]],  # Already a list from Ollama
            n_results=1
        )
        if test_results['documents']:
            logger.info(f"✓ Retrieval test successful")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to build vector store: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 70)
    print("Building Vector Store from Business Policies")
    print("=" * 70)
    print()
    
    # Check if custom file path provided
    import sys
    custom_file = None
    if len(sys.argv) > 1:
        custom_file = Path(sys.argv[1])
        print(f"Using custom file: {custom_file}")
    else:
        print(f"Using default file: {app_settings.RULES_FILE}")
    
    print()
    
    try:
        build_vectorstore(file_path=custom_file)
        print()
        print("=" * 70)
        print("✓ Vector Store Built Successfully!")
        print("=" * 70)
        print()
        print("Next steps:")
        print("1. Start the server: uvicorn src.main:app --host 0.0.0.0 --port 8000")
        print("2. Test retrieval: python -c 'from src.agents.rules_rag.query_vectorstore import rules_retriever; print(rules_retriever.retrieve_rules(\"fare limits\"))'")
        print()
        
    except Exception as e:
        print()
        print("=" * 70)
        print("✗ Vector Store Build Failed!")
        print("=" * 70)
        print(f"Error: {str(e)}")
        print()
        print("Troubleshooting:")
        print("1. Ensure the business policies file exists")
        print("2. Check file has content and proper encoding")
        print("3. Verify dependencies installed: pip install -r requirements.txt")
        sys.exit(1)
