import os
import json
from config.settings import settings
from config.logger import logger

# Try importing ChromaDB, fallback gracefully if not installed/configured properly
CHROMA_AVAILABLE = False
try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    CHROMA_AVAILABLE = True
except ImportError:
    logger.warning("chromadb package not found. Using lightweight JSON Vector memory fallback.")

class SemanticMemory:
    """
    Cognitive Long-term Semantic Vector Memory.
    Saves and searches memories (e.g. commands, device states, instructions) using semantic embeddings.
    """
    def __init__(self):
        self.chroma_client = None
        self.collection = None
        self.fallback_file = "d:/ai_robot/pi/storage/fallback_memory.json"
        
        if CHROMA_AVAILABLE:
            try:
                os.makedirs(settings.chromadb_dir, exist_ok=True)
                self.chroma_client = chromadb.PersistentClient(
                    path=settings.chromadb_dir,
                    settings=ChromaSettings(anonymized_telemetry=False)
                )
                self.collection = self.chroma_client.get_or_create_collection("central_ai_boss_memory")
                logger.info("ChromaDB Semantic Memory initialized successfully.")
            except Exception as e:
                logger.error(f"ChromaDB initialization failed, falling back to JSON: {e}")
                self.chroma_client = None
                
        if not self.collection:
            self._init_fallback_db()

    def _init_fallback_db(self):
        logger.info("Lightweight JSON Semantic Memory Fallback active.")
        os.makedirs(os.path.dirname(self.fallback_file), exist_ok=True)
        if not os.path.exists(self.fallback_file):
            with open(self.fallback_file, "w") as f:
                json.dump([], f)

    def add_memory(self, text: str, metadata: dict = None, memory_id: str = None):
        """Add a memory context into vector search."""
        if not memory_id:
            import uuid
            memory_id = str(uuid.uuid4())
        
        metadata = metadata or {}

        if self.collection:
            try:
                self.collection.add(
                    documents=[text],
                    metadatas=[metadata],
                    ids=[memory_id]
                )
                logger.info(f"Memory added to ChromaDB: '{text[:30]}...'")
                return
            except Exception as e:
                logger.error(f"Failed to add memory to ChromaDB: {e}")

        # Fallback implementation
        try:
            os.makedirs(os.path.dirname(self.fallback_file), exist_ok=True)
            memories = []
            if os.path.exists(self.fallback_file):
                try:
                    with open(self.fallback_file, "r", encoding="utf-8") as f:
                        memories = json.load(f)
                except Exception:
                    memories = []
            memories.append({
                "id": memory_id,
                "document": text,
                "metadata": metadata
            })
            with open(self.fallback_file, "w", encoding="utf-8") as f:
                json.dump(memories, f, indent=4)
            logger.info(f"Memory added to JSON Fallback: '{text[:30]}...'")
        except Exception as e:
            logger.error(f"Fallback write failed: {e}")

    def query_memories(self, query_text: str, limit: int = 3) -> list:
        """Search memories related semantically to query_text."""
        if self.collection:
            try:
                results = self.collection.query(
                    query_texts=[query_text],
                    n_results=limit
                )
                # Parse format
                documents = results.get("documents", [[]])[0]
                metadatas = results.get("metadatas", [[]])[0]
                return [{"document": doc, "metadata": meta} for doc, meta in zip(documents, metadatas)]
            except Exception as e:
                logger.error(f"ChromaDB query failed: {e}")

        # Fallback substring search (simple matching)
        try:
            if not os.path.exists(self.fallback_file):
                return []
            with open(self.fallback_file, "r", encoding="utf-8") as f:
                memories = json.load(f)
            query_words = query_text.lower().split()
            scored_memories = []
            for mem in memories:
                score = sum(1 for word in query_words if word in mem["document"].lower())
                if score > 0:
                    scored_memories.append((score, mem))
            
            # Sort by keyword match score
            scored_memories.sort(reverse=True, key=lambda x: x[0])
            return [{"document": m[1]["document"], "metadata": m[1]["metadata"]} for m in scored_memories[:limit]]
        except Exception as e:
            logger.error(f"Fallback query failed: {e}")
            return []

# Central semantic memory engine
semantic_memory = SemanticMemory()
