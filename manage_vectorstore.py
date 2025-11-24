#!/usr/bin/env python3
"""
Vector Store Management Script
Provides utilities to build, query, and inspect the RAG vector store.
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.agents.rules_rag.build_vectorstore import build_vectorstore, load_rules_text, chunk_text
from src.agents.rules_rag.query_vectorstore import rules_retriever
from src.config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def build_command(file_path: str = None):
    """Build vector store from policies file."""
    print("\n" + "=" * 70)
    print("BUILDING VECTOR STORE")
    print("=" * 70)
    
    try:
        target_file = Path(file_path) if file_path else None
        
        if target_file and not target_file.exists():
            print(f"\n✗ Error: File not found: {target_file}")
            return False
        
        build_vectorstore(file_path=target_file)
        
        print("\n" + "=" * 70)
        print("✓ SUCCESS - Vector store built successfully!")
        print("=" * 70)
        return True
        
    except Exception as e:
        print("\n" + "=" * 70)
        print("✗ FAILED - Vector store build failed!")
        print("=" * 70)
        print(f"Error: {str(e)}")
        return False


def query_command(query: str, top_k: int = 5):
    """Query the vector store."""
    print("\n" + "=" * 70)
    print("QUERYING VECTOR STORE")
    print("=" * 70)
    print(f"\nQuery: {query}")
    print(f"Top K: {top_k}")
    
    try:
        results = rules_retriever.retrieve_rules(query, top_k=top_k)
        
        print(f"\n✓ Retrieved {len(results)} results:")
        print("-" * 70)
        
        for i, result in enumerate(results, 1):
            print(f"\n[Result {i}]")
            print(result[:300] + "..." if len(result) > 300 else result)
            print("-" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Query failed: {str(e)}")
        return False


def info_command():
    """Display vector store information."""
    print("\n" + "=" * 70)
    print("VECTOR STORE INFORMATION")
    print("=" * 70)
    
    try:
        # Check if policies file exists
        policies_file = settings.RULES_FILE
        print(f"\nPolicies File: {policies_file}")
        
        if policies_file.exists():
            print(f"  ✓ File exists")
            with open(policies_file, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"  Size: {len(content)} characters")
            print(f"  Lines: {len(content.splitlines())}")
        else:
            print(f"  ✗ File not found")
        
        # Check vector store
        print(f"\nVector Store: {settings.VECTORSTORE_DIR}")
        
        if settings.VECTORSTORE_DIR.exists():
            print(f"  ✓ Directory exists")
        else:
            print(f"  ✗ Directory not found")
        
        # Try to connect
        try:
            count = rules_retriever.collection.count()
            metadata = rules_retriever.collection.metadata
            
            print(f"\nCollection: {rules_retriever.collection_name}")
            print(f"  Document count: {count}")
            print(f"  Metadata: {metadata}")
            
            # Test query
            print("\nTesting retrieval...")
            test_results = rules_retriever.retrieve_rules("test", top_k=1)
            if test_results:
                print("  ✓ Retrieval working")
            else:
                print("  ⚠ No results from test query")
                
        except Exception as e:
            print(f"\n  ✗ Cannot connect to vector store: {str(e)}")
            print("  Run: python manage_vectorstore.py build")
        
        print("\n" + "=" * 70)
        return True
        
    except Exception as e:
        print(f"\n✗ Info command failed: {str(e)}")
        return False


def preview_command(file_path: str = None):
    """Preview how text will be chunked."""
    print("\n" + "=" * 70)
    print("PREVIEW CHUNKING")
    print("=" * 70)
    
    try:
        target_file = Path(file_path) if file_path else settings.RULES_FILE
        
        if not target_file.exists():
            print(f"\n✗ Error: File not found: {target_file}")
            return False
        
        print(f"\nFile: {target_file}")
        
        # Load text
        with open(target_file, 'r', encoding='utf-8') as f:
            text = f.read()
        
        print(f"Total size: {len(text)} characters")
        
        # Chunk
        chunks = chunk_text(text)
        
        print(f"\n✓ Would create {len(chunks)} chunks")
        print(f"Chunk size range: {min(len(c) for c in chunks)} - {max(len(c) for c in chunks)} chars")
        print(f"Average chunk size: {sum(len(c) for c in chunks) / len(chunks):.0f} chars")
        
        # Show first few chunks
        print("\nFirst 3 chunks preview:")
        print("-" * 70)
        
        for i, chunk in enumerate(chunks[:3], 1):
            print(f"\n[Chunk {i}] ({len(chunk)} chars)")
            preview = chunk[:200] + "..." if len(chunk) > 200 else chunk
            print(preview)
            print("-" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Preview failed: {str(e)}")
        return False


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print("""
Vector Store Management Tool
============================

Usage:
  python manage_vectorstore.py <command> [options]

Commands:
  build [file]          Build vector store from policies file
                        Optional: specify custom file path
                        
  query <text> [k]      Query the vector store
                        k: number of results (default: 5)
                        
  info                  Display vector store information
  
  preview [file]        Preview how file will be chunked
                        Optional: specify custom file path

Examples:
  # Build from default file (sample_business_polices.txt)
  python manage_vectorstore.py build
  
  # Build from custom file
  python manage_vectorstore.py build path/to/policies.txt
  
  # Query for relevant policies
  python manage_vectorstore.py query "fare limits for employees"
  
  # Get vector store info
  python manage_vectorstore.py info
  
  # Preview chunking
  python manage_vectorstore.py preview
""")
        sys.exit(0)
    
    command = sys.argv[1].lower()
    
    if command == "build":
        file_path = sys.argv[2] if len(sys.argv) > 2 else None
        success = build_command(file_path)
        sys.exit(0 if success else 1)
        
    elif command == "query":
        if len(sys.argv) < 3:
            print("Error: Query text required")
            print("Usage: python manage_vectorstore.py query <text> [k]")
            sys.exit(1)
        
        query_text = sys.argv[2]
        top_k = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        success = query_command(query_text, top_k)
        sys.exit(0 if success else 1)
        
    elif command == "info":
        success = info_command()
        sys.exit(0 if success else 1)
        
    elif command == "preview":
        file_path = sys.argv[2] if len(sys.argv) > 2 else None
        success = preview_command(file_path)
        sys.exit(0 if success else 1)
        
    else:
        print(f"Unknown command: {command}")
        print("Run without arguments to see help")
        sys.exit(1)


if __name__ == "__main__":
    main()
