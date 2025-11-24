# User Chat Endpoint Documentation

## Overview

The `/api/user-chat` endpoint allows users to ask natural language questions about their validation results using AI. The orchestrator uses the session data and LLM to provide intelligent answers.

---

## Endpoint Details

### **POST** `/api/user-chat`

Ask questions about validation results, extracted data, policies, or any aspect of the invoice processing.

#### Request Parameters

**Query Parameters:**
- `session_id` (required): The session ID from a completed validation

**Request Body:**
```json
{
  "question": "Why was this document rejected?"
}
```

#### Response

```json
{
  "session_id": "sess_abc123def456",
  "question": "Why was this document rejected?",
  "answer": "Your document was rejected because...",
  "has_context": true,
  "context_items": 4
}
```

---

## How It Works

```
User Question
    ↓
Retrieve Session Data
    ↓
Build Context:
  - Extracted invoice data
  - Employee details
  - Validation results
  - Policy rules applied
  - Violations (if any)
    ↓
Call LLM (gemma3:27b)
    ↓
Generate Answer
    ↓
Return to User
```

---

## Example Questions

### 1. **Why was my document rejected?**
```bash
curl -X POST "http://localhost:8000/api/user-chat?session_id=sess_abc123" \
  -H "Content-Type: application/json" \
  -d '{"question": "Why was this document rejected?"}'
```

**Example Answer:**
> "Your document was rejected because the fare amount of ₹12,000 exceeds the maximum allowed limit of ₹10,000 for Senior level employees according to company policy."

---

### 2. **What is the maximum fare for L2 employee?**
```bash
curl -X POST "http://localhost:8000/api/user-chat?session_id=sess_abc123" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the maximum fare for L2 employee?"}'
```

**Example Answer:**
> "Based on the validation results, the maximum fare limit for your employee level (Senior/L2) is ₹10,000.00 per trip."

---

### 3. **Where is the employee traveling to?**
```bash
curl -X POST "http://localhost:8000/api/user-chat?session_id=sess_abc123" \
  -H "Content-Type: application/json" \
  -d '{"question": "Where is the employee traveling to?"}'
```

**Example Answer:**
> "According to the extracted invoice data, the employee is traveling from COIMBATORE to CHENNAI on 2024-01-25."

---

### 4. **What was the extracted fare amount?**
```bash
curl -X POST "http://localhost:8000/api/user-chat?session_id=sess_abc123" \
  -H "Content-Type: application/json" \
  -d '{"question": "What was the extracted fare amount?"}'
```

**Example Answer:**
> "The fare amount extracted from the invoice is ₹500.00 with a confidence score of 95.0%."

---

### 5. **What policies were checked?**
```bash
curl -X POST "http://localhost:8000/api/user-chat?session_id=sess_abc123" \
  -H "Content-Type: application/json" \
  -d '{"question": "What policies were checked during validation?"}'
```

**Example Answer:**
> "The validation checked the following policies: 1) Fare limits for Senior employees (₹10,000), 2) Original invoice requirements, 3) Travel authorization requirements, and 4) Expense documentation rules."

---

## Context Provided to LLM

The orchestrator automatically builds comprehensive context from the session:

```python
EXTRACTED INVOICE DATA:
- Passenger Name: Mohit Chandran
- Origin: COIMBATORE
- Destination: CHENNAI
- Travel Date: 2024-01-25
- Fare: ₹500.0
- Extraction Confidence: 95.0%

EMPLOYEE DETAILS:
- Name: Mohit Chandran
- Level: Senior
- Fare Limit: ₹10,000.00

VALIDATION RESULT:
- Status: APPROVED
- Remarks: Fare within limit. All policies compliant.

POLICY RULES APPLIED:
- Senior employees: fare limit ₹10,000
- Original invoices required
- Travel must be pre-approved
```

---

## Use Cases

### 1. **Understanding Rejections**
Users can ask why their document was rejected and get specific policy violations explained.

### 2. **Policy Clarification**
Users can inquire about specific policy rules, fare limits, or requirements for their employee level.

### 3. **Data Verification**
Users can verify what data was extracted from their invoice and check for accuracy.

### 4. **Route Information**
Users can ask about travel routes, dates, and destinations extracted from invoices.

### 5. **General Questions**
Users can ask any question about the validation process, and the AI will answer based on available context.

---

## Streamlit UI Integration

The chat feature is integrated into the Streamlit app:

1. **After Validation**: Chat section appears below results
2. **Example Questions**: Clickable examples to get started
3. **Chat History**: All Q&A pairs are preserved in session
4. **Clear History**: Reset chat conversation anytime

**UI Flow:**
```
┌─────────────────────────────────────┐
│  Validation Results Displayed       │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  💬 Ask Questions Section            │
│                                     │
│  [Example Questions ▼]              │
│                                     │
│  Your question: ________________    │
│  [🤔 Ask]  [🗑️ Clear]               │
│                                     │
│  Chat History:                      │
│  Q1: Why rejected?                  │
│  A1: Because fare exceeds...        │
└─────────────────────────────────────┘
```

---

## Error Handling

### Session Not Found
```json
{
  "detail": "Chat request failed: Session sess_xyz not found. Please process validation first."
}
```

**Solution:** Run validation before asking questions.

### No Context Available
If validation hasn't completed, the chat will inform the user that context is not available.

### LLM Timeout
If the LLM takes too long (>120s), a timeout error is returned.

---

## Configuration

### LLM Settings
- **Model**: gemma3:27b
- **Temperature**: 0.3 (factual responses)
- **Timeout**: 120 seconds
- **System Prompt**: Specialized for Q&A about validation results

### Response Characteristics
- **Accuracy**: Based on actual session data
- **Length**: Concise but complete answers
- **Style**: Helpful, professional, references specific data
- **Limitations**: Only answers based on available session context

---

## Testing

### Using Python Requests
```python
import requests

session_id = "sess_abc123"
question = "Why was this document rejected?"

response = requests.post(
    f"http://localhost:8000/api/user-chat?session_id={session_id}",
    json={"question": question}
)

if response.status_code == 200:
    result = response.json()
    print(f"Q: {result['question']}")
    print(f"A: {result['answer']}")
```

### Using cURL
```bash
curl -X POST \
  "http://localhost:8000/api/user-chat?session_id=sess_abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the passenger name?"
  }'
```

### Using Test Script
Run the provided test script:
```bash
cd /home/mohitchandran/Desktop/LIC_POC
.venv/bin/python test_chat_endpoint.py
```

---

## Performance

| Operation              | Time      |
|------------------------|-----------|
| Session Data Retrieval | < 1ms     |
| Context Building       | < 10ms    |
| LLM Generation         | 2-5s      |
| **Total**              | **2-5s**  |

---

## Best Practices

### 1. **Ask Specific Questions**
✅ "What is the maximum fare for L2 employees?"
❌ "Tell me everything"

### 2. **Use Natural Language**
✅ "Why was my document rejected?"
✅ "Where is the employee traveling?"
✅ "What was the extracted fare?"

### 3. **Reference Session Context**
The chat has access to:
- Extracted invoice data
- Employee information
- Validation results
- Applied policies
- Violations (if any)

### 4. **Check Context Availability**
Ensure validation has completed before asking questions.

---

## API Documentation

Full API documentation available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Look for the "chat" tag to see the endpoint details.

---

## Future Enhancements

Potential improvements:

1. **Multi-turn Conversations**: Remember previous questions in conversation
2. **Suggested Follow-ups**: Recommend related questions
3. **Voice Input**: Speech-to-text for questions
4. **Rich Responses**: Include charts, tables in answers
5. **Citation**: Reference specific policy documents
6. **Multi-language**: Support questions in multiple languages

---

## Support

For issues or questions about the chat endpoint:
1. Check session exists and validation completed
2. Review logs for LLM errors
3. Verify Ollama server is running
4. Ensure gemma3:27b model is loaded

---

**Version**: 1.1.0
**Date**: 24 November 2025
**Status**: Production Ready ✅
