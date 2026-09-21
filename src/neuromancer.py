import chromadb
import os
import uuid
import datetime
import logging
import json
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

class NeuromancerCore:
    """
    The Memory Engine. Uses a localized ChromaDB instance to store and retrieve
    vector embeddings of past tasks, successes, failures, and environment data.
    """
    def __init__(self, db_path: str = "./data/memory"):
        self.db_path = db_path
        os.makedirs(self.db_path, exist_ok=True)
        # Initialize the local persistent ChromaDB client
        self.client = chromadb.PersistentClient(path=self.db_path)
        
        # Create or get the main memory collection
        self.collection = self.client.get_or_create_collection(
            name="construct_memories",
            metadata={"description": "Stores outcomes and learnings from deployed Constructs."}
        )

    def store_memory(self, task_description: str, outcome: str, learnings: str, tags: list = None):
        """
        Embeds and stores a new memory.
        """
        if tags is None:
            tags = []
            
        memory_id = f"mem_{uuid.uuid4().hex[:12]}"
        timestamp = datetime.datetime.now().isoformat()
        
        # The document is what gets embedded. We combine task and learnings for semantic search.
        document = f"Task: {task_description}\nLearnings: {learnings}\nOutcome: {outcome}"
        
        metadata = {
            "timestamp": timestamp,
            "outcome": outcome,
            "tags": ",".join(tags)
        }
        
        try:
            self.collection.add(
                documents=[document],
                metadatas=[metadata],
                ids=[memory_id]
            )
            logger.info(f"Stored memory {memory_id} successfully.")
        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            raise
        return memory_id

    def store_node_intel(self, host: str, open_ports: Any, details: Any) -> str:
        """
        Embeds and stores structured reconnaissance intel about a discovered node in ChromaDB.
        """
        if isinstance(open_ports, (list, tuple, set)):
            ports_str = ", ".join(str(p) for p in open_ports)
        elif isinstance(open_ports, dict):
            ports_str = ", ".join(str(k) for k in open_ports.keys())
        else:
            ports_str = str(open_ports)

        details_str = json.dumps(details, indent=2) if isinstance(details, (dict, list)) else str(details)

        doc_id = f"node_{host.replace('.', '_').replace(':', '_').replace('/', '_')}_{uuid.uuid4().hex[:8]}"
        timestamp = datetime.datetime.now().isoformat()

        document = f"Node Intel Discovered:\nHost: {host}\nOpen Ports: {ports_str}\nDetails:\n{details_str}"

        metadata = {
            "timestamp": timestamp,
            "host": str(host),
            "open_ports": str(ports_str)[:500],
            "outcome": "discovered",
            "tags": f"node_intel,{host}"
        }

        try:
            self.collection.add(
                documents=[document],
                metadatas=[metadata],
                ids=[doc_id]
            )
            logger.info(f"Stored node intel for host {host} ({doc_id}) successfully.")
        except Exception as e:
            logger.error(f"Failed to store node intel for {host}: {e}")
            raise
        return doc_id

    def retrieve_relevant_memory(self, query: str, n_results: int = 3) -> list:
        """
        Searches the vector database for memories semantically similar to the query.
        Returns a list of formatted memory strings.
        """
        try:
            if not query or not query.strip():
                return []

            # If the collection is empty, return empty list
            if self.collection.count() == 0:
                return []
                
            # Ensure we don't request more results than exist
            actual_results = min(n_results, self.collection.count())
            if actual_results <= 0:
                return []
            
            results = self.collection.query(
                query_texts=[query],
                n_results=actual_results
            )
            
            memories = []
            # Robust empty check to avoid index errors
            if results and results.get('documents') and len(results['documents']) > 0:
                docs = results['documents'][0]
                if docs:
                    for doc in docs:
                        if doc is not None:
                            memories.append(doc)
                            
            return memories
        except Exception as e:
            logger.error(f"Failed to retrieve memory: {e}", exc_info=True)
            return []

# Singleton instance
memory_core = NeuromancerCore()

def store_node_intel(host: str, open_ports: Any, details: Any) -> str:
    """Convenience module function forwarding to singleton memory_core."""
    return memory_core.store_node_intel(host, open_ports, details)
