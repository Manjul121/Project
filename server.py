import os
import re
import json
import uuid
import math
import shutil
import hashlib
from typing import List, Dict, Any, Optional
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, Form, Header, HTTPException, Query, Depends, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import requests

# Document Parsers
import pypdf
import docx
import csv

try:
    import openpyxl
except ImportError:
    openpyxl = None

try:
    import pptx
except ImportError:
    pptx = None

app = FastAPI(title="DocuMind AI Backend", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
USERS_FILE = DATA_DIR / "users.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Max upload limit: 500 MB in bytes (extendable toward 1 GB)
MAX_UPLOAD_SIZE = 500 * 1024 * 1024  # 500 MB

# --- PERSISTENCE HELPERS ---
def load_json(filepath: Path, default: Any = None):
    if not filepath.exists():
        return default if default is not None else {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}

def save_json(filepath: Path, data: Any):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    temp_file = filepath.with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    temp_file.replace(filepath)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def get_server_settings() -> Dict[str, Any]:
    default_settings = {
        "apiKey": os.environ.get("GEMINI_API_KEY", ""),
        "model": "gemini-2.0-flash",
        "topK": 5,
        "chunkSize": 800,
        "chunkOverlap": 120
    }
    saved = load_json(SETTINGS_FILE, default_settings)
    return {**default_settings, **saved}

def save_server_settings(settings: Dict[str, Any]):
    current = get_server_settings()
    current.update(settings)
    save_json(SETTINGS_FILE, current)

# --- USER STORAGE HELPERS ---
def get_user_dir(user_id: str) -> Path:
    safe_uid = re.sub(r"[^a-zA-Z0-9_\-]", "_", user_id)
    udir = DATA_DIR / "users" / safe_uid
    udir.mkdir(parents=True, exist_ok=True)
    return udir

def get_user_docs(user_id: str) -> List[Dict[str, Any]]:
    docs_file = get_user_dir(user_id) / "documents.json"
    return load_json(docs_file, [])

def save_user_docs(user_id: str, docs: List[Dict[str, Any]]):
    docs_file = get_user_dir(user_id) / "documents.json"
    save_json(docs_file, docs)

def get_user_vectors(user_id: str) -> List[Dict[str, Any]]:
    vectors_file = get_user_dir(user_id) / "vectors.json"
    return load_json(vectors_file, [])

def save_user_vectors(user_id: str, vectors: List[Dict[str, Any]]):
    vectors_file = get_user_dir(user_id) / "vectors.json"
    save_json(vectors_file, vectors)

# --- TEXT TOKENIZATION & CHUNKING ---
def tokenize(text: str) -> List[str]:
    clean = re.sub(r"[^\w\s]", " ", text.lower())
    words = [w for w in clean.split() if len(w) > 1]
    return words

def chunk_text(text: str, doc_name: str, doc_id: str, page_num: int = 1, chunk_size_words: int = 220, overlap_words: int = 35) -> List[Dict[str, Any]]:
    """Progressive semantic chunking with overlap and exact page preservation."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n|\r\n\s*\r\n", text) if p.strip()]
    if not paragraphs:
        paragraphs = [text.strip()] if text.strip() else []

    chunks = []
    current_words = []
    
    for p_idx, p in enumerate(paragraphs):
        words = p.split()
        current_words.extend(words)

        if len(current_words) >= chunk_size_words or p_idx == len(paragraphs) - 1:
            chunk_str = " ".join(current_words)
            if len(chunk_str.strip()) > 15:
                chunk_id = f"chk_{doc_id}_{len(chunks) + 1}"
                chunks.append({
                    "id": chunk_id,
                    "docId": doc_id,
                    "docName": doc_name,
                    "page": page_num,
                    "text": chunk_str,
                    "wordCount": len(current_words),
                    "terms": tokenize(chunk_str)
                })
            current_words = current_words[-overlap_words:] if len(current_words) > overlap_words else []

    return chunks

# --- DOCUMENT PARSERS ---
def parse_pdf(file_path: Path, doc_name: str, doc_id: str) -> Dict[str, Any]:
    pages_text = []
    reader = pypdf.PdfReader(str(file_path))
    total_pages = len(reader.pages)
    total_extracted_chars = 0

    chunks = []
    for page_idx, page in enumerate(reader.pages, start=1):
        txt = page.extract_text() or ""
        total_extracted_chars += len(txt.strip())
        pages_text.append(f"[Page {page_idx}]\n{txt}")
        if txt.strip():
            page_chunks = chunk_text(txt, doc_name, doc_id, page_num=page_idx)
            chunks.extend(page_chunks)

    is_scanned = (total_extracted_chars < 30 and total_pages > 0)
    full_text = "\n\n".join(pages_text)

    return {
        "text": full_text,
        "pageCount": total_pages,
        "chunks": chunks,
        "isScanned": is_scanned
    }

def parse_docx(file_path: Path, doc_name: str, doc_id: str) -> Dict[str, Any]:
    doc = docx.Document(str(file_path))
    paras = []
    for p in doc.paragraphs:
        if p.text.strip():
            paras.append(p.text.strip())
    for t in doc.tables:
        for row in t.rows:
            row_txt = " | ".join(c.text.strip() for c in row.cells if c.text.strip())
            if row_txt:
                paras.append(row_txt)

    full_text = "\n\n".join(paras)
    # Estimate pages (~400 words per page)
    words = full_text.split()
    page_count = max(1, math.ceil(len(words) / 400))
    chunks = chunk_text(full_text, doc_name, doc_id, page_num=1)

    return {
        "text": full_text,
        "pageCount": page_count,
        "chunks": chunks,
        "isScanned": False
    }

def parse_csv_file(file_path: Path, doc_name: str, doc_id: str) -> Dict[str, Any]:
    rows = []
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        for row in reader:
            if row:
                rows.append(" | ".join(row))

    full_text = "\n".join(rows)
    page_count = max(1, math.ceil(len(rows) / 40))
    chunks = chunk_text(full_text, doc_name, doc_id, page_num=1)

    return {
        "text": full_text,
        "pageCount": page_count,
        "chunks": chunks,
        "isScanned": False
    }

def parse_text_file(file_path: Path, doc_name: str, doc_id: str) -> Dict[str, Any]:
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        full_text = f.read()

    words = full_text.split()
    page_count = max(1, math.ceil(len(words) / 450))
    chunks = chunk_text(full_text, doc_name, doc_id, page_num=1)

    return {
        "text": full_text,
        "pageCount": page_count,
        "chunks": chunks,
        "isScanned": False
    }

def parse_xlsx(file_path: Path, doc_name: str, doc_id: str) -> Dict[str, Any]:
    if not openpyxl:
        return parse_text_file(file_path, doc_name, doc_id)
    wb = openpyxl.load_workbook(str(file_path), data_only=True)
    all_sheets = []
    for sheet in wb.sheetnames:
        ws = wb[sheet]
        sheet_lines = [f"[Sheet: {sheet}]"]
        for row in ws.iter_rows(values_only=True):
            vals = [str(v).strip() for v in row if v is not None and str(v).strip()]
            if vals:
                sheet_lines.append(" | ".join(vals))
        all_sheets.append("\n".join(sheet_lines))

    full_text = "\n\n".join(all_sheets)
    page_count = max(1, len(wb.sheetnames))
    chunks = chunk_text(full_text, doc_name, doc_id, page_num=1)
    return {
        "text": full_text,
        "pageCount": page_count,
        "chunks": chunks,
        "isScanned": False
    }

def parse_pptx(file_path: Path, doc_name: str, doc_id: str) -> Dict[str, Any]:
    if not pptx:
        return parse_text_file(file_path, doc_name, doc_id)
    prs = pptx.Presentation(str(file_path))
    slides_text = []
    chunks = []
    for s_idx, slide in enumerate(prs.slides, start=1):
        slide_parts = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    if paragraph.text.strip():
                        slide_parts.append(paragraph.text.strip())
        s_txt = "\n".join(slide_parts)
        slides_text.append(f"[Slide {s_idx}]\n{s_txt}")
        if s_txt.strip():
            chunks.extend(chunk_text(s_txt, doc_name, doc_id, page_num=s_idx))

    full_text = "\n\n".join(slides_text)
    return {
        "text": full_text,
        "pageCount": len(prs.slides),
        "chunks": chunks,
        "isScanned": False
    }

# --- MULTILINGUAL & INTENT RETRIEVAL ENGINE ---
INTENT_EXPANSIONS = {
    "skills": ["skills", "skill", "technologies", "technology", "tools", "languages", "stack", "frameworks", "technical skills", "expertise", "competencies", "hunnar", "kabiliyat", "kya aata hai"],
    "education": ["education", "degree", "university", "college", "school", "bachelor", "master", "phd", "academic", "b.tech", "m.tech", "cgpa", "percentage", "shiksha", "padhai", "qualification"],
    "experience": ["experience", "work experience", "employment", "internship", "job", "career", "company", "role", "designation", "worked at", "responsibilities", "anubhav", "kaam", "kitna time"],
    "projects": ["projects", "project", "portfolio", "built", "developed", "created", "system", "application", "app", "model"],
    "summary": ["summary", "overview", "about", "profile", "bio", "background", "objective", "saar", "batao", "kya hai", "document about"],
    "certifications": ["certification", "certifications", "certificate", "licensed", "course", "training"],
    "contact": ["email", "phone", "mobile", "contact", "address", "linkedin", "github", "portfolio"],
    "salary": ["salary", "ctc", "compensation", "package", "stipend", "pay", "income"]
}

def expand_query_terms(query: str) -> List[str]:
    q_lower = query.lower()
    terms = set(tokenize(q_lower))

    # Add query words
    for word in q_lower.split():
        clean_w = re.sub(r"[^\w]", "", word)
        if len(clean_w) > 2:
            terms.add(clean_w)

    # Detect intents (e.g. "eske skills kya hai" -> intent "skills")
    for intent, synonyms in INTENT_EXPANSIONS.items():
        for syn in synonyms:
            if syn in q_lower:
                for s in synonyms:
                    for part in s.split():
                        if len(part) > 2:
                            terms.add(part)
                break

    return list(terms)

def retrieve_top_chunks(query: str, chunks: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
    if not chunks:
        return []

    expanded_terms = expand_query_terms(query)
    query_lower = query.lower()

    scored = []
    for c in chunks:
        c_text_lower = c["text"].lower()
        score = 0.0

        # Term frequency & exact phrase boost
        for t in expanded_terms:
            if t in c_text_lower:
                occurrences = c_text_lower.count(t)
                score += (occurrences * 2.0)

        # Exact substring boost for key words
        for word in query.split():
            clean_word = re.sub(r"[^\w]", "", word.lower())
            if len(clean_word) >= 4 and clean_word in c_text_lower:
                score += 3.5

        # Document name matching
        doc_name_lower = c["docName"].lower()
        for word in query.split():
            if len(word) > 3 and word.lower() in doc_name_lower:
                score += 4.0

        # Normalize by length
        norm_score = score / (math.sqrt(len(c["text"].split())) + 1)
        scored.append((norm_score, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = [item[1] for item in scored[:top_k]]
    return results

# --- GROUNDED DIRECT ANSWER GENERATOR ---
def generate_grounded_answer_gemini(query: str, chunks: List[Dict[str, Any]], api_key: str, model: str) -> Optional[str]:
    if not api_key or len(api_key.strip()) < 10:
        return None

    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key.strip()}"

    context_blocks = []
    for idx, c in enumerate(chunks, 1):
        context_blocks.append(f"[Document: {c['docName']} | Page: {c['page']} | Chunk: #{idx}]\n{c['text']}")
    context_str = "\n\n---\n\n".join(context_blocks)

    system_instruction = (
        "You are DocuMind AI, an intelligent, objective document question-answering assistant.\n"
        "Your absolute highest priority is ACCURACY and DIRECT GROUNDING in the provided retrieved document context.\n\n"
        "STRICT RULES:\n"
        "1. Answer the user's question directly, clearly, and concisely. No filler phrases, no generic introductions.\n"
        "2. If asked for skills, extract and list the exact skills mentioned in the document as clean bullet points.\n"
        "3. If asked for education, experience, or summary, state the exact facts from the text.\n"
        "4. NEVER invent, assume, or hallucinate facts not stated in the document. If the document does not mention the requested information (such as salary, age, specific metrics not present), state clearly:\n"
        "   \"I couldn't find [topic] in the uploaded document.\"\n"
        "5. Language adaptation: If the user asks in Hindi or Hinglish (e.g. 'eske skills kya hai', 'iska summary batao', 'candidate ki education kya hai'), respond naturally in the same style/language while maintaining factual accuracy.\n"
        "6. Always append the exact source citation at the end in this format:\n"
        "   Source: <filename> — Page <page_number>\n"
        "   (If multiple documents/pages were used, cite each: Source: doc1.pdf — Page 1, doc2.pdf — Page 3)"
    )

    user_prompt = f"Retrieved Document Context:\n{context_str}\n\nUser Question:\n{query}"

    body = {
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "generationConfig": {
            "temperature": 0.15,
            "maxOutputTokens": 1024
        }
    }

    try:
        resp = requests.post(endpoint, json=body, timeout=25)
        if resp.status_code == 200:
            data = resp.json()
            candidate = data.get("candidates", [{}])[0]
            answer_text = candidate.get("content", {}).get("parts", [{}])[0].get("text", "")
            if answer_text:
                return answer_text.strip()
    except Exception as e:
        print(f"[Gemini API Error] {e}")

    return None

def generate_local_grounded_answer(query: str, chunks: List[Dict[str, Any]]) -> str:
    """Accurate offline extraction fallback. Zero generic boilerplate!"""
    if not chunks:
        return "I couldn't find relevant information in the uploaded documents to answer your question."

    q_lower = query.lower()
    top_chunk = chunks[0]
    doc_name = top_chunk["docName"]
    page_num = top_chunk["page"]

    combined_text = "\n".join(c["text"] for c in chunks)
    lines = [line.strip() for line in combined_text.splitlines() if line.strip()]

    # 1. Skills question (e.g. "eske skills kya hai", "what skills are mentioned")
    if any(k in q_lower for k in ["skill", "technologies", "tools", "languages", "tech stack", "hunnar", "kya aata"]):
        extracted_skills = []
        is_in_skills_section = False
        
        for line in lines:
            line_l = line.lower()
            if any(header in line_l for header in ["skill", "technical skill", "technologies", "core competencies", "tools & technologies", "programming languages"]):
                is_in_skills_section = True
                # Clean header line if it contains skills inline
                after_colon = line.split(":", 1)
                if len(after_colon) > 1 and len(after_colon[1].strip()) > 2:
                    raw_items = re.split(r"[,•|\n;]+", after_colon[1])
                    for item in raw_items:
                        item_clean = item.strip().strip("•-* ")
                        if 1 < len(item_clean) < 40 and item_clean not in extracted_skills:
                            extracted_skills.append(item_clean)
                continue

            if is_in_skills_section:
                # Stop if next major section
                if any(sec in line_l for sec in ["experience", "education", "projects", "employment", "certifications", "hobbies", "personal details"]) and len(line) < 30:
                    break
                raw_items = re.split(r"[,•|\n;]+", line)
                for item in raw_items:
                    item_clean = item.strip().strip("•-* ")
                    if 1 < len(item_clean) < 40 and item_clean not in extracted_skills:
                        extracted_skills.append(item_clean)

        if extracted_skills:
            bullet_points = "\n".join(f"• {s}" for s in extracted_skills[:15])
            is_hindi = any(w in q_lower for w in ["kya", "hai", "batao", "eske", "iske"])
            heading = f"Document me diye gaye skills ({doc_name}):" if is_hindi else f"Skills mentioned in {doc_name}:"
            return f"{heading}\n\n{bullet_points}\n\nSource: {doc_name} — Page {page_num}"
        else:
            # Look for lines containing programming keywords
            known_tech = ["Python", "JavaScript", "TypeScript", "React", "Node", "SQL", "HTML", "CSS", "Java", "C++", "Machine Learning", "Data Science", "Git", "Docker", "AWS", "FastAPI", "MongoDB", "PostgreSQL", "Excel"]
            found = [tech for tech in known_tech if re.search(r"\b" + re.escape(tech) + r"\b", combined_text, re.IGNORECASE)]
            if found:
                bullet_points = "\n".join(f"• {s}" for s in found)
                return f"Skills identified in {doc_name}:\n\n{bullet_points}\n\nSource: {doc_name} — Page {page_num}"

    # 2. Education question
    if any(k in q_lower for k in ["education", "degree", "college", "university", "school", "shiksha", "padhai"]):
        edu_lines = []
        is_in_edu = False
        for line in lines:
            line_l = line.lower()
            if "education" in line_l or "academic" in line_l or "qualification" in line_l:
                is_in_edu = True
                continue
            if is_in_edu:
                if any(sec in line_l for sec in ["experience", "skills", "projects", "certifications"]) and len(line) < 30:
                    break
                if len(line) > 3:
                    edu_lines.append(f"• {line}")

        if edu_lines:
            edu_text = "\n".join(edu_lines[:6])
            is_hindi = any(w in q_lower for w in ["kya", "hai", "batao", "eske", "iske"])
            heading = f"Education details ({doc_name}):" if not is_hindi else f"Education details document me:"
            return f"{heading}\n\n{edu_text}\n\nSource: {doc_name} — Page {page_num}"

    # 3. Experience question
    if any(k in q_lower for k in ["experience", "work", "job", "company", "role", "anubhav", "kaam"]):
        exp_lines = []
        is_in_exp = False
        for line in lines:
            line_l = line.lower()
            if any(h in line_l for h in ["experience", "work history", "employment"]):
                is_in_exp = True
                continue
            if is_in_exp:
                if any(sec in line_l for sec in ["education", "skills", "projects", "certifications", "interests"]) and len(line) < 30:
                    break
                if len(line) > 5:
                    exp_lines.append(f"• {line}")

        if exp_lines:
            exp_text = "\n".join(exp_lines[:8])
            return f"Experience details mentioned in {doc_name}:\n\n{exp_text}\n\nSource: {doc_name} — Page {page_num}"

    # 4. Salary / Missing info prevention (Anti-hallucination)
    if any(k in q_lower for k in ["salary", "ctc", "package", "stipend", "compensation"]):
        has_salary = any(re.search(r"(\$|₹|inr|usd|lpa|salary|ctc)\s*\d+", line, re.IGNORECASE) for line in lines)
        if not has_salary:
            return f"I couldn't find salary or compensation information in the uploaded document.\n\nSource: {doc_name} — Page {page_num}"

    # 5. Summary / General Question: extract the most relevant sentences directly
    sentences = re.split(r"(?<=[.!?])\s+", top_chunk["text"])
    key_sentences = [s.strip() for s in sentences if len(s.strip()) > 20][:4]
    if key_sentences:
        summary_bullets = "\n".join(f"• {s}" for s in key_sentences)
        is_hindi = any(w in q_lower for w in ["kya", "hai", "batao", "eske", "iske", "saar"])
        title = f"Document summary ({doc_name}):" if not is_hindi else f"Document ka saar ({doc_name}):"
        return f"{title}\n\n{summary_bullets}\n\nSource: {doc_name} — Page {page_num}"

    return f"Information from {doc_name}:\n\n{top_chunk['text'][:350]}...\n\nSource: {doc_name} — Page {page_num}"

# --- API ROUTES ---

@app.post("/api/auth/register")
async def api_register(payload: Dict[str, Any]):
    name = (payload.get("name") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    if not name or not email or not password:
        raise HTTPException(status_code=400, detail="Name, email, and password are required")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    users = load_json(USERS_FILE, [])
    if any(u.get("email") == email for u in users):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    new_user = {
        "id": "usr_" + uuid.uuid4().hex[:12],
        "name": name,
        "email": email,
        "passwordHash": hash_password(password),
        "createdAt": uuid.uuid1().time
    }
    users.append(new_user)
    save_json(USERS_FILE, users)

    return {
        "success": True,
        "user": {
            "id": new_user["id"],
            "name": new_user["name"],
            "email": new_user["email"]
        }
    }

@app.post("/api/auth/login")
async def api_login(payload: Dict[str, Any]):
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    users = load_json(USERS_FILE, [])
    user = next((u for u in users if u.get("email") == email and u.get("passwordHash") == hash_password(password)), None)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    return {
        "success": True,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"]
        }
    }

@app.get("/api/documents")
async def api_get_documents(user_id: str = Query(...)):
    if not user_id:
        return []
    docs = get_user_docs(user_id)
    # Return document list without heavy raw text
    return [{
        "id": d["id"],
        "name": d["name"],
        "type": d["type"],
        "size": d["size"],
        "pageCount": d.get("pageCount", 1),
        "isScanned": d.get("isScanned", False),
        "status": "Ready"
    } for d in docs]

@app.post("/api/upload")
async def api_upload_document(
    file: UploadFile = File(...),
    user_id: str = Form(...)
):
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required for upload isolation.")

    # 1. Sanitize filename
    clean_name = Path(file.filename).name
    clean_name = re.sub(r"[^\w\.\-\_ ]", "_", clean_name)
    ext = clean_name.split(".")[-1].lower() if "." in clean_name else ""

    allowed_exts = {"pdf", "docx", "doc", "txt", "csv", "xlsx", "pptx", "md"}
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"Unsupported file type (.{ext}). Supported types: PDF, DOCX, TXT, CSV, XLSX, PPTX.")

    # 2. Save in user directory with streaming (supports up to 500 MB)
    user_files_dir = get_user_dir(user_id) / "files"
    user_files_dir.mkdir(parents=True, exist_ok=True)
    doc_id = "doc_" + uuid.uuid4().hex[:10]
    saved_path = user_files_dir / f"{doc_id}_{clean_name}"

    total_bytes = 0
    with open(saved_path, "wb") as out_file:
        while True:
            chunk = await file.read(1024 * 1024)  # 1 MB chunk
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > MAX_UPLOAD_SIZE:
                out_file.close()
                if saved_path.exists():
                    saved_path.unlink()
                raise HTTPException(status_code=413, detail=f"File exceeds maximum allowed size of 500 MB.")
            out_file.write(chunk)

    # 3. Format file size
    size_str = (
        f"{total_bytes / (1024*1024):.1f} MB" if total_bytes >= 1024 * 1024
        else f"{total_bytes / 1024:.0f} KB"
    )

    # 4. Parse document based on extension
    try:
        if ext == "pdf":
            parsed = parse_pdf(saved_path, clean_name, doc_id)
        elif ext in ["docx", "doc"]:
            parsed = parse_docx(saved_path, clean_name, doc_id)
        elif ext == "csv":
            parsed = parse_csv_file(saved_path, clean_name, doc_id)
        elif ext == "xlsx":
            parsed = parse_xlsx(saved_path, clean_name, doc_id)
        elif ext == "pptx":
            parsed = parse_pptx(saved_path, clean_name, doc_id)
        else:
            parsed = parse_text_file(saved_path, clean_name, doc_id)
    except Exception as e:
        if saved_path.exists():
            saved_path.unlink()
        raise HTTPException(status_code=500, detail="Couldn't read this document. Please verify the file is not corrupted.")

    # 5. Update user documents list
    docs = get_user_docs(user_id)
    # Remove existing doc with same name if any
    docs = [d for d in docs if d.get("name") != clean_name]

    doc_record = {
        "id": doc_id,
        "name": clean_name,
        "type": ext if ext in ["pdf", "docx", "csv", "xlsx", "pptx"] else "txt",
        "size": size_str,
        "filePath": str(saved_path),
        "pageCount": parsed["pageCount"],
        "isScanned": parsed.get("isScanned", False),
        "status": "Ready"
    }
    docs.append(doc_record)
    save_user_docs(user_id, docs)

    # 6. Update user vector store
    vectors = get_user_vectors(user_id)
    vectors = [v for v in vectors if v.get("docName") != clean_name]
    vectors.extend(parsed["chunks"])
    save_user_vectors(user_id, vectors)

    return {
        "success": True,
        "document": {
            "id": doc_id,
            "name": clean_name,
            "type": doc_record["type"],
            "size": size_str,
            "pageCount": parsed["pageCount"],
            "isScanned": parsed.get("isScanned", False),
            "status": "Ready"
        }
    }

@app.delete("/api/documents/{doc_id}")
async def api_delete_document(doc_id: str, user_id: str = Query(...)):
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required.")

    docs = get_user_docs(user_id)
    doc_to_remove = next((d for d in docs if d["id"] == doc_id), None)
    if not doc_to_remove:
        return {"success": True, "message": "Document already removed."}

    # Delete physical file
    file_path = doc_to_remove.get("filePath")
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass

    # Filter out from documents.json
    docs = [d for d in docs if d["id"] != doc_id]
    save_user_docs(user_id, docs)

    # Filter out from vectors.json
    vectors = get_user_vectors(user_id)
    vectors = [v for v in vectors if v.get("docId") != doc_id and v.get("docName") != doc_to_remove["name"]]
    save_user_vectors(user_id, vectors)

    return {"success": True, "removedDocId": doc_id}

@app.post("/api/chat")
async def api_chat(payload: Dict[str, Any]):
    user_id = payload.get("userId")
    query = (payload.get("query") or "").strip()

    if not user_id:
        raise HTTPException(status_code=400, detail="User ID required.")
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    vectors = get_user_vectors(user_id)
    docs = get_user_docs(user_id)

    if not docs or not vectors:
        return {
            "answer": "No documents uploaded yet. Please upload a document to begin asking questions.",
            "sources": []
        }

    settings = get_server_settings()
    top_k = int(settings.get("topK", 5))
    retrieved = retrieve_top_chunks(query, vectors, top_k=top_k)

    # Try Gemini 2.0 Flash first if API key configured
    api_key = settings.get("apiKey", "")
    model = settings.get("model", "gemini-2.0-flash")
    answer = None

    if api_key and len(api_key.strip()) > 10:
        answer = generate_grounded_answer_gemini(query, retrieved, api_key, model)

    # If Gemini wasn't available, use high-precision local grounded synthesis
    if not answer:
        answer = generate_local_grounded_answer(query, retrieved)

    # Collect unique sources
    seen_sources = set()
    sources = []
    for c in retrieved:
        src_key = f"{c['docName']}:{c['page']}"
        if src_key not in seen_sources:
            seen_sources.add(src_key)
            sources.append({
                "docName": c["docName"],
                "page": c["page"]
            })

    return {
        "answer": answer,
        "sources": sources
    }

@app.get("/api/settings")
async def api_get_settings():
    settings = get_server_settings()
    masked_key = ""
    if settings.get("apiKey"):
        key = settings["apiKey"]
        masked_key = key[:6] + "..." + key[-4:] if len(key) > 10 else "***"
    return {
        "hasKey": bool(settings.get("apiKey")),
        "maskedKey": masked_key,
        "model": settings.get("model", "gemini-2.0-flash"),
        "topK": settings.get("topK", 5)
    }

@app.post("/api/settings")
async def api_save_settings(payload: Dict[str, Any]):
    new_settings = {}
    if "apiKey" in payload and payload["apiKey"].strip():
        new_settings["apiKey"] = payload["apiKey"].strip()
    if "model" in payload:
        new_settings["model"] = payload["model"]
    if "topK" in payload:
        new_settings["topK"] = int(payload["topK"])

    save_server_settings(new_settings)
    return {"success": True, "message": "Settings saved securely on server."}

@app.post("/api/settings/test")
async def api_test_connection(payload: Dict[str, Any]):
    key = payload.get("apiKey") or get_server_settings().get("apiKey", "")
    if not key or len(key.strip()) < 10:
        raise HTTPException(status_code=400, detail="Please enter a valid API key.")

    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key.strip()}"
    test_body = {
        "contents": [{"parts": [{"text": "Hello"}]}],
        "generationConfig": {"maxOutputTokens": 5}
    }
    try:
        resp = requests.post(endpoint, json=test_body, timeout=10)
        if resp.status_code == 200:
            return {"success": True, "status": "Connected · Ready"}
        else:
            err = resp.json().get("error", {}).get("message", "Authentication error")
            return {"success": False, "status": f"Connection failed: {err}"}
    except Exception as e:
        return {"success": False, "status": f"Connection timed out: {str(e)}"}

# Serve frontend static assets from current directory
app.mount("/", StaticFiles(directory=str(BASE_DIR), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
