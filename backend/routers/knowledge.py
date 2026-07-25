from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
import os, time, uuid
from knowledge.document_parser import parse_file, chunk_text
from knowledge.vector_store import store
from skills.llm_client import get_embedding

router = APIRouter(tags=["knowledge"])

@router.post("/knowledge/upload")
async def upload_document(file: UploadFile = File(...)):
    # 保存文件
    ext = os.path.splitext(file.filename)[1]
    doc_id = f"doc_{uuid.uuid4().hex[:8]}"
    filepath = f"./data/knowledge_base/{doc_id}{ext}"
    os.makedirs("./data/knowledge_base", exist_ok=True)
    
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)
    
    # 解析文本
    text = parse_file(filepath)
    if not text or text.startswith("["):
        return {"error": f"解析失败: {text}"}
    
    # 分块+embedding
    chunks = chunk_text(text)
    for i, chunk in enumerate(chunks):
        embedding = await get_embedding(chunk[:1000])
        store.add(f"{doc_id}_chunk_{i}", chunk, embedding, {"source": file.filename, "doc_id": doc_id})
    
    return {"doc_id": doc_id, "chunks": len(chunks), "filename": file.filename, "text_length": len(text)}

@router.get("/knowledge/documents")
async def list_documents():
    docs = store.list_docs()
    # 按doc_id去重
    seen = set()
    unique = []
    for d in docs:
        did = d.get("metadata", {}).get("doc_id", d["id"])
        if did not in seen:
            seen.add(did)
            unique.append(d)
    return unique

@router.post("/knowledge/search")
async def search_knowledge(query: str = Form(...), top_k: int = Form(5)):
    embedding = await get_embedding(query)
    results = store.search(embedding, top_k)
    return [{"text": r["text"][:500], "score": round(r["score"], 4), "source": r.get("metadata", {}).get("source", "")} for r in results]

@router.delete("/knowledge/documents/{doc_id}")
async def delete_document(doc_id: str):
    # 删除所有chunk
    docs = [d for d in store.documents if d.get("metadata", {}).get("doc_id") == doc_id]
    for d in docs:
        store.delete(d["id"])
    return {"deleted": len(docs)}
