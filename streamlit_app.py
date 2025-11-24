"""
Simple Streamlit App for AI Travel Invoice Validator
Test interface for uploading documents and viewing validation results
"""

import streamlit as st
import requests
import pandas as pd
from pathlib import Path
import json

# Configuration
API_BASE_URL = "http://localhost:8000/api"

# Page config
st.set_page_config(
    page_title="Travel Invoice Validator",
    page_icon="✈️",
    layout="wide"
)

# Title
st.title("✈️ AI Travel Invoice Validator")
st.markdown("---")

# Initialize session state
if 'session_id' not in st.session_state:
    st.session_state.session_id = None
if 'validation_results' not in st.session_state:
    st.session_state.validation_results = None

# Function to create session
def create_session():
    try:
        print(f"[LOG] Calling API to create session at {API_BASE_URL}/session")
        response = requests.post(f"{API_BASE_URL}/session")
        print(f"[LOG] Session API response status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            session_id = data['session_id']
            print(f"[LOG] Session created successfully: {session_id}")
            return session_id
        else:
            print(f"[LOG ERROR] Failed to create session: {response.text}")
            st.error(f"Failed to create session: {response.text}")
            return None
    except Exception as e:
        print(f"[LOG ERROR] Exception connecting to API: {e}")
        st.error(f"Error connecting to API: {e}")
        return None

# Function to upload file
def upload_file(file, file_type, session_id):
    try:
        print(f"[LOG] Uploading {file_type}: {file.name} (size: {file.size} bytes)")
        files = {'file': (file.name, file, file.type)}
        endpoint = f"{API_BASE_URL}/upload-{file_type}?session_id={session_id}"
        print(f"[LOG] Upload endpoint: {endpoint}")
        response = requests.post(endpoint, files=files)
        print(f"[LOG] Upload response status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"[LOG] File uploaded successfully: {file.name}")
            return True, "File uploaded successfully"
        else:
            print(f"[LOG ERROR] Upload failed: {response.text}")
            return False, f"Upload failed: {response.text}"
    except Exception as e:
        print(f"[LOG ERROR] Upload exception: {e}")
        return False, f"Error: {e}"

# Function to process and validate
def process_validation(session_id):
    try:
        print(f"[LOG] Starting validation for session: {session_id}")
        endpoint = f"{API_BASE_URL}/process-validation?session_id={session_id}"
        print(f"[LOG] Validation endpoint: {endpoint}")
        response = requests.post(endpoint)
        print(f"[LOG] Validation response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"[LOG] Validation completed successfully")
            print(f"[LOG] Response keys: {list(result.keys())}")
            return True, result
        else:
            print(f"[LOG ERROR] Validation failed: {response.text}")
            return False, f"Validation failed: {response.text}"
    except Exception as e:
        print(f"[LOG ERROR] Validation exception: {e}")
        return False, f"Error: {e}"

# Create two columns for file upload
col1, col2 = st.columns(2)

with col1:
    st.subheader("📄 Upload Invoice PDF")
    invoice_file = st.file_uploader(
        "Choose invoice PDF file",
        type=['pdf'],
        key='invoice'
    )
    
with col2:
    st.subheader("📊 Upload Proposal Excel")
    excel_file = st.file_uploader(
        "Choose proposal Excel file",
        type=['xlsx', 'xls'],
        key='excel'
    )

st.markdown("---")

# Process button
if st.button("🚀 Process & Validate", type="primary", use_container_width=True):
    if invoice_file is None or excel_file is None:
        st.error("⚠️ Please upload both invoice PDF and proposal Excel files!")
    else:
        # Clear previous results
        st.session_state.validation_results = None
        
        # Create a container for step-by-step progress
        progress_container = st.container()
        
        with progress_container:
            # STEP 1: Create Session
            st.write("### 📋 STEP 1: Creating Session")
            with st.spinner("Creating session..."):
                if st.session_state.session_id is None:
                    st.session_state.session_id = create_session()
                
                if not st.session_state.session_id:
                    st.error("❌ Failed to create session. Please try again.")
                    st.stop()
                
                st.success(f"✅ Session created: `{st.session_state.session_id}`")
                print(f"[LOG] Session created: {st.session_state.session_id}")
            
            st.markdown("---")
            
            # STEP 2: Upload Files
            st.write("### 📤 STEP 2: Uploading Files")
            
            # Upload invoice
            with st.spinner("Uploading invoice PDF..."):
                print(f"[LOG] Uploading invoice: {invoice_file.name}")
                success, message = upload_file(invoice_file, 'invoice', st.session_state.session_id)
                if not success:
                    st.error(f"❌ Invoice upload failed: {message}")
                    print(f"[LOG] Invoice upload failed: {message}")
                    st.stop()
                else:
                    st.success(f"✅ Invoice uploaded: `{invoice_file.name}`")
                    print(f"[LOG] Invoice uploaded successfully")
            
            # Upload excel
            with st.spinner("Uploading proposal Excel..."):
                print(f"[LOG] Uploading proposal: {excel_file.name}")
                success, message = upload_file(excel_file, 'proposal', st.session_state.session_id)
                if not success:
                    st.error(f"❌ Excel upload failed: {message}")
                    print(f"[LOG] Excel upload failed: {message}")
                    st.stop()
                else:
                    st.success(f"✅ Proposal uploaded: `{excel_file.name}`")
                    print(f"[LOG] Proposal uploaded successfully")
            
            st.markdown("---")
            
            # STEP 3: Extract & Validate
            st.write("### 🤖 STEP 3: AI Processing")
            
            with st.spinner("🔄 Extracting data from invoice (using gemma3:27b with vision)..."):
                print(f"[LOG] Starting validation pipeline...")
                success, result = process_validation(st.session_state.session_id)
                
                if not success:
                    st.error(f"❌ Processing failed: {result}")
                    print(f"[LOG] Processing failed: {result}")
                    st.stop()
            
            # STEP 4: Display Extracted Data FIRST
            st.markdown("---")
            st.write("### 🎯 STEP 4: Extraction Results")
            
            print(f"[LOG] Extraction completed, displaying results...")
            
            # Show extracted data in an expander
            with st.expander("📋 **View Extracted Invoice Data (JSON)**", expanded=True):
                st.json(result)
            
            # Display key extracted fields prominently
            st.write("#### 📊 Key Extracted Fields:")
            
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                st.metric(
                    label="Passenger Name",
                    value=result.get('name', 'N/A')
                )
                st.metric(
                    label="Travel Date", 
                    value=result.get('date', 'N/A')
                )
            
            with col_b:
                st.metric(
                    label="From",
                    value=result.get('from', 'N/A')
                )
                st.metric(
                    label="To",
                    value=result.get('to', 'N/A')
                )
            
            with col_c:
                st.metric(
                    label="Fare Amount",
                    value=f"₹{result.get('fare', 0.0):,.2f}"
                )
                st.metric(
                    label="Confidence",
                    value=f"{result.get('confidence', 0.0)*100:.1f}%"
                )
            
            st.markdown("---")
            
            # STEP 5: Validation Status
            st.write("### ✅ STEP 5: Policy Validation")
            
            status = result.get('validation_status', 'unknown')
            
            if status == 'approved':
                st.success(f"🎉 **APPROVED** - Invoice complies with policy")
            else:
                st.error(f"❌ **REJECTED** - Policy violations found")
            
            st.write(f"**Remarks:** {result.get('remarks', 'No remarks')}")
            
            # Store results
            st.session_state.validation_results = result
            st.success("✅ Processing completed!")
            print(f"[LOG] All steps completed successfully")

# Chat section - Ask questions about validation
if st.session_state.validation_results and st.session_state.session_id:
    st.markdown("---")
    st.header("💬 Ask Questions About Your Validation")
    
    st.write("You can ask questions about the validation results, extracted data, or policies.")
    
    # Initialize chat history in session state
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Example questions
    with st.expander("💡 Example Questions"):
        st.markdown("""
        - Why was this document rejected?
        - What is the maximum fare for my employee level?
        - Where is the employee traveling to?
        - What was the extracted fare amount?
        - What policies were checked?
        - What is the passenger name?
        - When is the travel date?
        """)
    
    # Chat input
    user_question = st.text_input(
        "Your question:",
        placeholder="e.g., Why was my document rejected?",
        key="chat_input"
    )
    
    col_ask, col_clear = st.columns([3, 1])
    
    with col_ask:
        if st.button("🤔 Ask", type="primary", use_container_width=True):
            if user_question:
                with st.spinner("Thinking..."):
                    print(f"[LOG] Asking question: {user_question}")
                    
                    try:
                        # Call chat API
                        response = requests.post(
                            f"{API_BASE_URL}/user-chat?session_id={st.session_state.session_id}",
                            json={"question": user_question}
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            answer = result['answer']
                            
                            # Add to chat history
                            st.session_state.chat_history.append({
                                'question': user_question,
                                'answer': answer
                            })
                            
                            print(f"[LOG] Answer received: {len(answer)} chars")
                            st.rerun()
                        else:
                            st.error(f"Chat request failed: {response.text}")
                            print(f"[LOG ERROR] Chat failed: {response.text}")
                    
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
                        print(f"[LOG ERROR] Chat exception: {str(e)}")
            else:
                st.warning("Please enter a question")
    
    with col_clear:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()
    
    # Display chat history
    if st.session_state.chat_history:
        st.markdown("---")
        st.subheader("💬 Chat History")
        
        for i, chat in enumerate(reversed(st.session_state.chat_history)):
            with st.container():
                st.markdown(f"**Q{len(st.session_state.chat_history) - i}:** {chat['question']}")
                st.info(chat['answer'])
                st.markdown("")

# Display results (Summary Section - Details already shown above during processing)
if st.session_state.validation_results:
    st.markdown("---")
    st.header("� Download Results")
    
    results = st.session_state.validation_results
    
    st.write("All validation steps completed! You can download the results in different formats:")
    
    # Download buttons
    col_dl1, col_dl2 = st.columns(2)
    
    with col_dl1:
        # Download results as JSON
        st.download_button(
            label="📥 Download Full Results (JSON)",
            data=json.dumps(results, indent=2),
            file_name="validation_results.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col_dl2:
        # Create simple CSV
        csv_data = f"Field,Value\n"
        csv_data += f"Passenger Name,{results.get('name', 'N/A')}\n"
        csv_data += f"From,{results.get('from', 'N/A')}\n"
        csv_data += f"To,{results.get('to', 'N/A')}\n"
        csv_data += f"Date,{results.get('date', 'N/A')}\n"
        csv_data += f"Fare,{results.get('fare', 0.0)}\n"
        csv_data += f"Validation Status,{results.get('validation_status', 'unknown')}\n"
        csv_data += f"Remarks,{results.get('remarks', '')}\n"
        
        st.download_button(
            label="📥 Download Summary (CSV)",
            data=csv_data,
            file_name="validation_summary.csv",
            mime="text/csv",
            use_container_width=True
        )

# Sidebar with info
with st.sidebar:
    st.header("ℹ️ Information")
    st.markdown("""
    ### How to use:
    1. Upload invoice PDF
    2. Upload proposal Excel
    3. Click "Process & Validate"
    4. View results in table format
    
    ### Excel Format:
    Required columns:
    - name
    - employee_level
    - fare_limit
    
    ### API Status:
    """)
    
    # Check API health
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code == 200:
            st.success("✅ API Connected")
            health = response.json()
            st.write(f"**Ollama:** {health.get('ollama', 'N/A')}")
            st.write(f"**RAG:** {health.get('rag', 'N/A')}")
        else:
            st.error("❌ API Unreachable")
    except:
        st.error("❌ API Offline")
    
    st.markdown("---")
    
    if st.button("🔄 Reset Session"):
        st.session_state.session_id = None
        st.session_state.validation_results = None
        st.rerun()
    
    st.markdown("---")
    st.caption("AI Travel Invoice Validator v1.0")
