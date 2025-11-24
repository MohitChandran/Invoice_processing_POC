# API Endpoints

| # | Method | Endpoint | Purpose | Request | Response |
|---|--------|----------|---------|---------|----------|
| 1 | GET | `/health` | Health check | - | `{"status":"healthy"}` |
| 2 | GET | `/` | List all endpoints | - | `{"endpoints":[...]}` |
| 3 | POST | `/api/session` | Create session | - | `{"session_id":"sess_xxx"}` |
| 4 | POST | `/api/upload-invoice` | Upload invoice PDF | `?session_id=xxx` + File | `{"file_id":"inv_xxx"}` |
| 5 | POST | `/api/upload-proposal` | Upload proposal Excel | `?session_id=xxx` + File | `{"file_id":"prop_xxx"}` |
| 6 | POST | `/api/process-validation` | Run full validation | `?session_id=xxx` + Body | Validation results JSON |
| 7 | GET | `/api/session/{id}` | Get session status | - | Session data JSON |
| 8 | GET | `/api/download/{session_id}` | Download results | `?format=json/csv` | File download |
| 9 | POST | `/api/user-chat` | Ask questions about results | `?session_id=xxx` + `{"question":"..."}` | `{"answer":"..."}` |

## Typical Flow
```
1. POST /api/session → get session_id
2. POST /api/upload-invoice?session_id=xxx → upload PDF
3. POST /api/upload-proposal?session_id=xxx → upload Excel
4. POST /api/process-validation?session_id=xxx → validate (invoice_id, proposal_id in body)
5. POST /api/user-chat?session_id=xxx → ask questions
6. GET /api/download/xxx?format=json → download results
```

## Test
```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/api/session
```

**Docs**: http://localhost:8000/docs
