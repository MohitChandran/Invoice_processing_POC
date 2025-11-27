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
            data = response.json()
            file_id = data.get('file_id')
            print(f"[LOG] File uploaded successfully: {file.name} → {file_id}")
            return True, file_id
        else:
            print(f"[LOG ERROR] Upload failed: {response.text}")
            return False, None
    except Exception as e:
        print(f"[LOG ERROR] Upload exception: {e}")
        return False, None

# Function to upload multiple invoices
def upload_invoices_batch(files, session_id):
    try:
        print(f"[LOG] Uploading batch of {len(files)} invoices")
        
        # Prepare files for multipart upload
        files_data = [('files', (f.name, f, f.type)) for f in files]
        endpoint = f"{API_BASE_URL}/upload-invoices-batch?session_id={session_id}"
        print(f"[LOG] Batch upload endpoint: {endpoint}")
        
        response = requests.post(endpoint, files=files_data)
        print(f"[LOG] Batch upload response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"[LOG] Batch upload completed: {result['uploaded']}/{result['total']} successful")
            return True, result
        else:
            print(f"[LOG ERROR] Batch upload failed: {response.text}")
            return False, f"Batch upload failed: {response.text}"
    except Exception as e:
        print(f"[LOG ERROR] Batch upload exception: {e}")
        return False, f"Error: {e}"

# Function to process batch validation
def process_batch_validation(invoice_ids, proposal_id, session_id):
    try:
        print(f"[LOG] Starting batch validation for {len(invoice_ids)} invoices")
        
        # Build query parameters
        invoice_params = "&".join([f"invoice_ids={iid}" for iid in invoice_ids])
        endpoint = f"{API_BASE_URL}/process-batch-validation?{invoice_params}&proposal_id={proposal_id}&session_id={session_id}"
        print(f"[LOG] Batch validation endpoint: {endpoint}")
        
        response = requests.post(endpoint)
        print(f"[LOG] Batch validation response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"[LOG] Batch validation completed: {result['processed']}/{result['total_invoices']} processed")
            return True, result
        else:
            print(f"[LOG ERROR] Batch validation failed: {response.text}")
            return False, f"Batch validation failed: {response.text}"
    except Exception as e:
        print(f"[LOG ERROR] Batch validation exception: {e}")
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
    st.subheader("📄 Upload Invoice PDFs")
    st.info("💡 **NEW**: You can now upload multiple invoice files at once!")
    invoice_files = st.file_uploader(
        "Choose one or more invoice PDF files",
        type=['pdf', 'jpg', 'jpeg', 'png'],
        key='invoices',
        accept_multiple_files=True,
        help="Upload multiple travel invoices for batch processing"
    )
    
    if invoice_files:
        st.write(f"📦 Selected {len(invoice_files)} file(s)")
        for idx, f in enumerate(invoice_files, 1):
            st.write(f"{idx}. {f.name} ({f.size:,} bytes)")
    
with col2:
    st.subheader("📊 Upload Proposal Excel")
    st.info("📋 Excel must contain: employee_level, name, from, to, relation, fare, mode_of_transport, status")
    excel_file = st.file_uploader(
        "Choose proposal Excel file",
        type=['xlsx', 'xls'],
        key='excel',
        help="Excel with all travelers (employees + dependents)"
    )

st.markdown("---")

# Process button
if st.button("🚀 Process & Validate", type="primary", use_container_width=True):
    if not invoice_files or excel_file is None:
        st.error("⚠️ Please upload at least one invoice PDF and a proposal Excel file!")
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
            
            # Upload invoices (batch or single)
            with st.spinner(f"Uploading {len(invoice_files)} invoice file(s)..."):
                print(f"[LOG] Uploading {len(invoice_files)} invoices")
                success, result = upload_invoices_batch(invoice_files, st.session_state.session_id)
                if not success:
                    st.error(f"❌ Invoice upload failed: {result}")
                    print(f"[LOG] Invoice upload failed: {result}")
                    st.stop()
                else:
                    st.success(f"✅ Invoices uploaded: {result['uploaded']}/{result['total']} successful")
                    invoice_ids = result['file_ids']
                    print(f"[LOG] {len(invoice_ids)} invoices uploaded successfully")
                    
                    # Show upload details
                    with st.expander("View upload details"):
                        for item in result['results']:
                            if item['status'] == 'success':
                                st.write(f"✅ {item['filename']} → `{item['file_id']}`")
                            else:
                                st.write(f"❌ {item['filename']}: {item.get('error', 'Unknown error')}")
            
            # Upload excel
            with st.spinner("Uploading proposal Excel..."):
                print(f"[LOG] Uploading proposal: {excel_file.name}")
                success, proposal_id = upload_file(excel_file, 'proposal', st.session_state.session_id)
                if not success:
                    st.error(f"❌ Excel upload failed")
                    print(f"[LOG] Excel upload failed")
                    st.stop()
                else:
                    st.success(f"✅ Proposal uploaded: `{excel_file.name}`")
                    print(f"[LOG] Proposal uploaded successfully: {proposal_id}")
            
            st.markdown("---")
            
            # STEP 3: Extract & Validate
            st.write("### 🤖 STEP 3: AI Processing")
            
            # Determine if batch or single processing
            is_batch = len(invoice_files) > 1
            
            if is_batch:
                st.info(f"📦 Processing {len(invoice_files)} invoices in batch mode")
                
                with st.spinner(f"🔄 Extracting and validating {len(invoice_files)} invoices..."):
                    print(f"[LOG] Starting batch validation pipeline...")
                    success, batch_result = process_batch_validation(invoice_ids, proposal_id, st.session_state.session_id)
                    
                    if not success:
                        st.error(f"❌ Batch processing failed: {batch_result}")
                        print(f"[LOG] Batch processing failed: {batch_result}")
                        st.stop()
                    
                    print(f"[LOG] Batch processing completed: {batch_result['processed']}/{batch_result['total_invoices']}")
            else:
                st.info("Processing single invoice")
                
                with st.spinner("🔄 Extracting data from invoice (using VLM)..."):
                    print(f"[LOG] Starting validation pipeline...")
                    success, result = process_validation(st.session_state.session_id)
                    
                    if not success:
                        st.error(f"❌ Processing failed: {result}")
                        print(f"[LOG] Processing failed: {result}")
                        st.stop()
            
            # STEP 4: Display Results
            st.markdown("---")
            st.write("### 🎯 STEP 4: Validation Results")
            
            if is_batch:
                # Display batch results
                print(f"[LOG] Displaying batch results...")
                
                st.write(f"#### 📦 Batch Summary")
                col_summary1, col_summary2, col_summary3 = st.columns(3)
                
                with col_summary1:
                    st.metric("Total Invoices", batch_result['total_invoices'])
                with col_summary2:
                    st.metric("Processed", batch_result['processed'], delta_color="normal")
                with col_summary3:
                    st.metric("Failed", batch_result['failed'], delta_color="inverse")
                
                st.markdown("---")
                
                # Display results table
                st.write("#### 📊 Individual Results")
                
                # Prepare data for table
                table_data = []
                for item in batch_result['results']:
                    if item['status'] == 'success' and item['result']:
                        r = item['result']
                        table_data.append({
                            'Passenger': r.get('name', 'N/A'),
                            'From': r.get('from', 'N/A'),
                            'To': r.get('to', 'N/A'),
                            'Fare': f"₹{r.get('fare', 0.0):,.2f}",
                            'Relation': r.get('relation', 'N/A'),
                            'Status': r.get('validation_status', 'unknown').upper(),
                            'Remarks': r.get('remarks', 'N/A')[:50] + '...' if len(r.get('remarks', '')) > 50 else r.get('remarks', 'N/A')
                        })
                    else:
                        table_data.append({
                            'Passenger': 'ERROR',
                            'From': '-',
                            'To': '-',
                            'Fare': '-',
                            'Relation': '-',
                            'Status': 'ERROR',
                            'Remarks': item.get('error', 'Unknown error')[:50]
                        })
                
                df = pd.DataFrame(table_data)
                st.dataframe(df, use_container_width=True)
                
                # Detailed view for each invoice
                st.write("#### 🔍 Detailed Results")
                for idx, item in enumerate(batch_result['results'], 1):
                    if item['status'] == 'success' and item['result']:
                        r = item['result']
                        status = r.get('validation_status', 'unknown')
                        
                        with st.expander(f"Invoice {idx}: {r.get('name', 'N/A')} - {status.upper()}", expanded=False):
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.write("**Travel Details:**")
                                st.write(f"- From: {r.get('from', 'N/A')}")
                                st.write(f"- To: {r.get('to', 'N/A')}")
                                st.write(f"- Date: {r.get('date', 'N/A')}")
                                st.write(f"- Mode: {r.get('mode_of_transport', 'N/A')}")
                            
                            with col2:
                                st.write("**Employee Details:**")
                                st.write(f"- Name: {r.get('employee_name', 'N/A')}")
                                st.write(f"- Level: {r.get('employee_level', 'N/A')}")
                                st.write(f"- Relation: {r.get('relation', 'N/A')}")
                                st.write(f"- Status: {r.get('status', 'N/A')}")
                            
                            with col3:
                                st.write("**Financial:**")
                                st.write(f"- Fare: ₹{r.get('fare', 0.0):,.2f}")
                                st.write(f"- Limit: ₹{r.get('fare_limit', 0.0):,.2f}")
                                st.write(f"- Confidence: {r.get('confidence', 0.0)*100:.1f}%")
                            
                            if status == 'approved':
                                st.success(f"✅ APPROVED: {r.get('remarks', 'No remarks')}")
                            else:
                                st.error(f"❌ REJECTED: {r.get('remarks', 'No remarks')}")
                                if r.get('violations'):
                                    st.write("**Violations:**")
                                    for v in r['violations']:
                                        st.write(f"- {v}")
                
                # Store batch results
                st.session_state.validation_results = batch_result
                
            else:
                # Display single result (existing logic)
                print(f"[LOG] Extraction completed, displaying single result...")
                
                # Show extracted data in an expander
                with st.expander("📋 **View Full JSON Response**", expanded=False):
                    st.json(result)
                
                # Display key extracted fields prominently
                st.write("#### 📊 Travel Details:")
                
                col_a, col_b, col_c = st.columns(3)
                
                with col_a:
                    st.metric(label="Passenger Name", value=result.get('name', 'N/A'))
                    st.metric(label="Travel Date", value=result.get('date', 'N/A'))
                
                with col_b:
                    st.metric(label="From", value=result.get('from', 'N/A'))
                    st.metric(label="To", value=result.get('to', 'N/A'))
                
                with col_c:
                    st.metric(label="Fare Amount", value=f"₹{result.get('fare', 0.0):,.2f}")
                    st.metric(label="Mode", value=result.get('mode_of_transport', 'N/A'))
                
                # Display Employee Details
                st.write("#### 👤 Employee Details:")
                
                col_emp1, col_emp2, col_emp3 = st.columns(3)
                
                with col_emp1:
                    st.metric(label="Employee Name", value=result.get('employee_name', 'N/A'))
                    st.metric(label="Employee Level", value=result.get('employee_level', 'N/A'))
                
                with col_emp2:
                    st.metric(label="Relation Type", value=result.get('relation', 'N/A'))
                    st.metric(label="Status", value=result.get('status', 'N/A'))
                
                with col_emp3:
                    st.metric(label="Fare Limit", value=f"₹{result.get('fare_limit', 0.0):,.2f}")
                    st.metric(label="Confidence", value=f"{result.get('confidence', 0.0)*100:.1f}%")
                
                st.markdown("---")
                
                # Validation Status
                st.write("### ✅ Validation Result")
                
                status = result.get('validation_status', 'unknown')
                
                if status == 'approved':
                    st.success(f"🎉 **APPROVED** - Invoice complies with policy")
                else:
                    st.error(f"❌ **REJECTED** - Policy violations found")
                
                st.write(f"**Remarks:** {result.get('remarks', 'No remarks')}")
                
                if result.get('violations'):
                    st.write("**Violations:**")
                    for v in result['violations']:
                        st.write(f"- {v}")
                
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
        csv_data += f"Employee Name,{results.get('employee_name', 'N/A')}\n"
        csv_data += f"Employee Level,{results.get('employee_level', 'N/A')}\n"
        csv_data += f"Fare Limit,{results.get('fare_limit', 0.0)}\n"
        csv_data += f"Relation Member,{results.get('relation_member', 'N/A')}\n"
        csv_data += f"Relation,{results.get('relation', 'N/A')}\n"
        csv_data += f"Status,{results.get('status', 'N/A')}\n"
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
    - relation_member (dependent name)
    - relation (wife/husband/son/daughter/mother/father)
    - status (approved/rejected)
    
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
