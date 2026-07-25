"""向量存储 - 基于本地JSON文件的简易向量数据库"""
import json
import os
import math
from typing import List, Tuple

KNOWLEDGE_DIR = os.getenv("KNOWLEDGE_DIR", "./data/knowledge_base")

class VectorStore:
    def __init__(self, name: str = "default"):
        self.name = name
        self.filepath = os.path.join(KNOWLEDGE_DIR, f"{name}_vectors.json")
        self.documents = []
        self._load()
    
    def _load(self):
        os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
        if os.path.exists(self.filepath):
            with open(self.filepath, "r", encoding="utf-8") as f:
                self.documents = json.load(f)
    
    def _save(self):
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self.documents, f, ensure_ascii=False, indent=2)
    
    def add(self, doc_id: str, text: str, embedding: list, metadata: dict = None):
        """添加文档向量"""
        self.documents.append({
            "id": doc_id,
            "text": text,
            "embedding": embedding,
            "metadata": metadata or {}
        })
        self._save()
    
    def search(self, query_embedding: list, top_k: int = 5) -> List[dict]:
        """余弦相似度搜索"""
        if not self.documents:
            return []
        
        results = []
        for doc in self.documents:
            score = self._cosine_similarity(query_embedding, doc["embedding"])
            results.append({**doc, "score": score})
        
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
    
    def delete(self, doc_id: str):
        """删除文档"""
        self.documents = [d for d in self.documents if d["id"] != doc_id]
        self._save()
    
    def list_docs(self) -> list:
        """列出所有文档"""
        return [{"id": d["id"], "text_preview": d["text"][:100], "metadata": d.get("metadata", {})} for d in self.documents]
    
    @staticmethod
    def _cosine_similarity(a: list, b: list) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

# 全局实例
store = VectorStore("knowledge_base")
