╔══════════════════════════════════════════════════════════════════════════════╗
║                   AI TRAVEL INVOICE VALIDATOR - QUICK REFERENCE              ║
╚══════════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────────┐
│ 🌐 ACCESS POINTS                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ Streamlit UI:  http://localhost:8501                                        │
│ FastAPI:       http://localhost:8000                                        │
│ API Docs:      http://localhost:8000/docs                                   │
│ Ollama:        http://192.168.10.200:11434                                  │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ 🚀 QUICK START                                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. Open: http://localhost:8501                                              │
│ 2. Upload Invoice PDF                                                       │
│ 3. Upload Proposal Excel                                                    │
│ 4. Click "🚀 Process & Validate"                                            │
│ 5. View extraction results (NEW!)                                           │
│ 6. Check validation status                                                  │
│ 7. Download results                                                         │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ 📋 WORKFLOW STEPS                                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│ STEP 1: Creating Session                                                    │
│   → Generates unique session ID                                             │
│                                                                              │
│ STEP 2: Uploading Files                                                     │
│   → Invoice PDF uploaded                                                    │
│   → Proposal Excel uploaded                                                 │
│                                                                              │
│ STEP 3: AI Processing                                                       │
│   → gemma3:27b extracts data (15-30s)                                       │
│                                                                              │
│ STEP 4: Extraction Results ⭐ NEW!                                           │
│   → View extracted JSON                                                     │
│   → See metric cards (Name, From, To, Date, Fare, Confidence)              │
│   → Verify accuracy before validation                                       │
│                                                                              │
│ STEP 5: Policy Validation                                                   │
│   → RAG-based policy check                                                  │
│   → Approved/Rejected status                                                │
│   → Detailed remarks                                                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ 🎯 KEY FEATURES                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│ ✅ Extraction JSON display (NEW!)                                           │
│ ✅ Visual metric cards                                                       │
│ ✅ Confidence scoring                                                        │
│ ✅ Step-by-step progress                                                     │
│ ✅ Comprehensive logging                                                     │
│ ✅ Session tracking                                                          │
│ ✅ Download results (JSON/CSV)                                               │
│ ✅ RAG-based policy validation                                               │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ 🔧 MODELS & CONFIG                                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ Vision Model:  gemma3:27b (16.2GB, Q4_K_M)                                  │
│ Text Model:    gemma3:27b (same model!)                                     │
│ Embeddings:    mxbai-embed-large (0.6GB, F16)                               │
│ Vector Store:  ChromaDB (10 policy chunks)                                  │
│ LLM Timeout:   120 seconds                                                  │
│ Vision Timeout: 60 seconds                                                  │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ 📊 EXTRACTION DISPLAY (NEW!)                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│ JSON Expander:                                                              │
│   {                                                                         │
│     "name": "Mohit Chandran",                                               │
│     "from": "COIMBATORE",                                                   │
│     "to": "CHENNAI",                                                        │
│     "date": "2024-01-25",                                                   │
│     "fare": 500.0,                                                          │
│     "confidence": 0.95                                                      │
│   }                                                                         │
│                                                                              │
│ Metric Cards:                                                               │
│   ┌──────────────┬──────────────┬──────────────┐                           │
│   │ Passenger    │ Travel Date  │ Fare Amount  │                           │
│   │ Mohit        │ 2024-01-25   │ ₹500.00      │                           │
│   ├──────────────┼──────────────┼──────────────┤                           │
│   │ From         │ To           │ Confidence   │                           │
│   │ COIMBATORE   │ CHENNAI      │ 95.0%        │                           │
│   └──────────────┴──────────────┴──────────────┘                           │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ 📝 LOGGING (NEW!)                                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│ Streamlit Console:                                                          │
│   [LOG] Session created successfully: sess_abc123                           │
│   [LOG] Uploading invoice: ticket.pdf (size: 51234 bytes)                  │
│   [LOG] File uploaded successfully                                          │
│   [LOG] Starting validation for session: sess_abc123                        │
│   [LOG] Validation completed successfully                                   │
│                                                                              │
│ FastAPI Console:                                                            │
│   ══════════════════════════════════════════════════════════                │
│   🚀 STARTING VALIDATION WORKFLOW                                           │
│   ══════════════════════════════════════════════════════════                │
│   📁 STEP 1: Loading Files...                                               │
│   ✅ Files loaded successfully                                               │
│   🔍 STEP 2: Extracting Invoice Data...                                     │
│   ✅ Extraction completed! (Confidence: 95.0%)                               │
│   👤 STEP 3: Matching Employee...                                           │
│   ✅ Employee matched!                                                       │
│   📋 STEP 4: Validating Against Policy...                                   │
│   ✅ Validation completed! (Status: APPROVED)                                │
│   ══════════════════════════════════════════════════════════                │
│   ✅ VALIDATION WORKFLOW COMPLETED                                           │
│   ══════════════════════════════════════════════════════════                │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ 🚨 TROUBLESHOOTING                                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ Issue: API Offline                                                          │
│   → Start FastAPI: uvicorn src.main:app --reload --port 8000               │
│                                                                              │
│ Issue: Low Confidence (<50%)                                                │
│   → Use high-quality scan                                                   │
│   → Ensure text is readable                                                 │
│   → Manually verify extracted data                                          │
│                                                                              │
│ Issue: Extraction Timeout                                                   │
│   → Check Ollama server status                                              │
│   → Wait and retry                                                          │
│   → Reduce image size if >5MB                                               │
│                                                                              │
│ Issue: Validation Rejected                                                  │
│   → Review extraction JSON                                                  │
│   → Check employee details                                                  │
│   → Read remarks for violations                                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ 📥 DOWNLOAD OPTIONS                                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ Full Results (JSON):                                                        │
│   → Complete validation data                                                │
│   → All extracted fields                                                    │
│   → Machine-readable                                                        │
│                                                                              │
│ Summary (CSV):                                                              │
│   → Key fields only                                                         │
│   → Excel-compatible                                                        │
│   → Reporting-friendly                                                      │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ 📖 DOCUMENTATION                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ SUMMARY.md       → Implementation overview                                  │
│ CHANGES_LOG.md   → Detailed changelog                                       │
│ QUICKSTART.md    → User guide                                               │
│ QUICKREF.md      → This reference card                                      │
│ README.md        → Project documentation                                    │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ ⏱️ PERFORMANCE                                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│ Session Creation:      < 1 second                                           │
│ File Upload:           1-2 seconds                                          │
│ Extraction (gemma3):   15-30 seconds                                        │
│ Employee Matching:     < 1 second                                           │
│ Policy Validation:     5-10 seconds                                         │
│ Total Time:            ~20-40 seconds                                       │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ 📂 TEST FILES                                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│ Invoice:  /home/mohitchandran/Downloads/mohit_dummyticket.pdf              │
│ Proposal: (Your employee Excel file)                                       │
│ Policies: smaple_business_policies.txt                                      │
└─────────────────────────────────────────────────────────────────────────────┘

╔══════════════════════════════════════════════════════════════════════════════╗
║                             VERSION INFORMATION                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ Version:        1.1.0                                                        ║
║ Date:           2024-11-24                                                   ║
║ Key Feature:    Extraction JSON display before validation                   ║
║ Enhancement:    Comprehensive logging throughout pipeline                   ║
║ Status:         ✅ Production Ready                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
