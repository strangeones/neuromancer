import chromadb
from chromadb.config import Settings
import os
import uuid
import datetime

class NeuromancerCore:
    """
    The Memory Engine. Uses a localized ChromaDB instance to store and retrieve
    vector embeddings of past tasks, successes, failures, and environment data.
    """
    def __init__(self, db_path: str = "./data/memory"):
        self.db_path = db_path
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
        
        self.collection.add(
            documents=[document],
            metadatas=[metadata],
            ids=[memory_id]
        )
        return memory_id

    def retrieve_relevant_memory(self, query: str, n_results: int = 3) -> list:
        """
        Searches the vector database for memories semantically similar to the query.
        Returns a list of formatted memory strings.
        """
        # If the collection is empty, return empty list
        if self.collection.count() == 0:
            return []
            
        # Ensure we don't request more results than exist
        actual_results = min(n_results, self.collection.count())
        
        results = self.collection.query(
            query_texts=[query],
            n_results=actual_results
        )
        
        memories = []
        if results['documents'] and len(results['documents']) > 0:
            for i, doc in enumerate(results['documents'][0]):
                memories.append(doc)
                
        return memories

# Singleton instance
memory_core = NeuromancerCore()
