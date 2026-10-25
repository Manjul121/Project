# 🤖 DocuMind AI

### Intelligent Document Intelligence & Grounded Question Answering

DocuMind AI is an enterprise-grade document intelligence platform designed to extract, index, and answer questions directly from your documents (PDF, DOCX, TXT, CSV, XLSX, PPTX up to **500 MB** per file) with zero hallucination and verified source citations.

---

## 🚀 Key Highlights

* 📄 **Large-File Document Support**: Handles PDF, DOCX, TXT, CSV, XLSX, and PPTX up to **500 MB** per file using batched streaming ingestion.
* 🧠 **Production RAG Pipeline**:
  * Page-accurate semantic chunking (600–900 tokens with contextual overlap).
  * Multilingual intent matching supporting English, Hindi, and Hinglish naturally (e.g., *"eske skills kya hai"*, *"candidate ki education kya hai"*).
  * Hybrid semantic vector retrieval with exact source grounding.
  * Anti-hallucination guardrails: if an answer is not in the document, it explicitly tells you rather than guessing.
* 🎯 **Direct, Grounded Answers**: Clean, direct factual answers (such as bulleted skills lists, education, or summaries) with clickable page citations (`Source: document.pdf — Page 1`).
* 🔐 **Isolated User Workspaces**: Real authentication (registration & login) with strict per-user document and vector isolation.
* 🤖 **Centered 3D Assistant**: Integrated, beautifully framed 3D robot animation without clutter or third-party branding.
* ⚙️ **Secure Server-Side Settings**: Configure your API key and retrieval parameters safely on the server side without client-side exposure.

---

## 🛠️ System Architecture

```text
User Upload (up to 500 MB Streaming)
             ↓
Backend Validation & Multi-Format Parsing (PDF, DOCX, CSV, TXT, XLSX, PPTX)
             ↓
Semantic Chunking (Page metadata & overlap preservation)
             ↓
Persistent User-Partitioned Vector Storage (data/users/{userId}/)
             ↓
User Query (English, Hindi, or Hinglish)
             ↓
Hybrid Semantic Retrieval & Intent Expansion
             ↓
Context-Grounded LLM / Factual Extraction Pipeline
             ↓
Direct Factual Answer + Clickable Page Citation
```

---

## 🚀 Running the Application

### 1. Start the Backend Server

```bash
python -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Access the Application

Open your browser and navigate to:
**[http://localhost:8000](http://localhost:8000)**

### 3. Workflow

1. **Sign Up / Log In**: Create your personal account.
2. **Upload Documents**: Choose any document (PDF, DOCX, CSV, TXT, XLSX, PPTX).
3. **Ask Questions**: Ask natural questions in English or Hinglish (e.g., *"What skills are mentioned in this document?"*, *"eske skills kya hai"*, *"summarize key findings"*).
4. **Inspect Sources**: Click on any citation badge to view the relevant document context.
