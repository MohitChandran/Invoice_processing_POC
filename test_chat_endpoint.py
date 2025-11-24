"""
Test script for the new /api/user-chat endpoint.
Demonstrates asking questions about validation results.
"""

import requests
import json
import time

API_BASE_URL = "http://localhost:8000/api"

def create_session():
    """Create a new session."""
    print("📋 Creating session...")
    response = requests.post(f"{API_BASE_URL}/session")
    if response.status_code == 200:
        session_id = response.json()["session_id"]
        print(f"✅ Session created: {session_id}\n")
        return session_id
    else:
        print(f"❌ Failed to create session: {response.text}")
        return None

def upload_files(session_id, invoice_path, proposal_path):
    """Upload invoice and proposal files."""
    print("📤 Uploading files...")
    
    # Upload invoice
    with open(invoice_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(
            f"{API_BASE_URL}/upload-invoice?session_id={session_id}",
            files=files
        )
        if response.status_code != 200:
            print(f"❌ Invoice upload failed: {response.text}")
            return False
        print(f"✅ Invoice uploaded")
    
    # Upload proposal
    with open(proposal_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(
            f"{API_BASE_URL}/upload-proposal?session_id={session_id}",
            files=files
        )
        if response.status_code != 200:
            print(f"❌ Proposal upload failed: {response.text}")
            return False
        print(f"✅ Proposal uploaded\n")
    
    return True

def process_validation(session_id):
    """Process validation."""
    print("🔄 Processing validation...")
    response = requests.post(f"{API_BASE_URL}/process-validation?session_id={session_id}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Validation completed!\n")
        print(f"📊 VALIDATION RESULT:")
        print(f"   Name: {result.get('name')}")
        print(f"   From: {result.get('from')}")
        print(f"   To: {result.get('to')}")
        print(f"   Date: {result.get('date')}")
        print(f"   Fare: ₹{result.get('fare')}")
        print(f"   Status: {result.get('validation_status').upper()}")
        print(f"   Remarks: {result.get('remarks')}\n")
        return True, result
    else:
        print(f"❌ Validation failed: {response.text}")
        return False, None

def ask_question(session_id, question):
    """Ask a question about the validation."""
    print(f"\n{'='*80}")
    print(f"💬 ASKING QUESTION")
    print(f"{'='*80}")
    print(f"Question: {question}")
    print(f"{'-'*80}\n")
    
    payload = {
        "question": question
    }
    
    response = requests.post(
        f"{API_BASE_URL}/user-chat?session_id={session_id}",
        json=payload
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"🤖 ANSWER:")
        print(f"{result['answer']}\n")
        print(f"{'='*80}\n")
        return result['answer']
    else:
        print(f"❌ Chat request failed: {response.text}\n")
        print(f"{'='*80}\n")
        return None

def main():
    """Main test flow."""
    print("\n" + "="*80)
    print("🧪 TESTING USER CHAT ENDPOINT")
    print("="*80 + "\n")
    
    # Paths (update these to your actual files)
    invoice_path = "/home/mohitchandran/Downloads/mohit_dummyticket.pdf"
    proposal_path = "/home/mohitchandran/Desktop/LIC_POC/proposal.xlsx"  # Update this!
    
    # Step 1: Create session
    session_id = create_session()
    if not session_id:
        print("❌ Test failed: Could not create session")
        return
    
    # Step 2: Upload files
    if not upload_files(session_id, invoice_path, proposal_path):
        print("❌ Test failed: Could not upload files")
        return
    
    # Step 3: Process validation
    success, validation_result = process_validation(session_id)
    if not success:
        print("❌ Test failed: Validation failed")
        return
    
    # Wait a moment for session data to settle
    time.sleep(2)
    
    print("\n" + "="*80)
    print("🎯 NOW TESTING CHAT FUNCTIONALITY")
    print("="*80)
    
    # Step 4: Ask various questions
    questions = [
        "Why was this document rejected?",
        "What is the maximum fare for L2 employee?",
        "Where is the employee traveling to?",
        "What was the extracted fare amount?",
        "What policies were checked during validation?",
        "What is the passenger name in the invoice?",
        "When is the travel date?",
        "What is the employee's level?"
    ]
    
    for question in questions:
        ask_question(session_id, question)
        time.sleep(1)  # Brief pause between questions
    
    print("\n" + "="*80)
    print("✅ TEST COMPLETED!")
    print("="*80 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
