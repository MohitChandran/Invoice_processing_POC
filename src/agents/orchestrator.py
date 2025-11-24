"""
Orchestrator Agent - Coordinates all agents and manages sessions.
"""

import uuid
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from src.agents.extraction_agent import extraction_agent
from src.agents.excel_agent import excel_agent
from src.agents.policy_agent import policy_agent
from src.services.file_storage import file_storage

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages validation sessions with file-based persistence."""
    
    def __init__(self):
        self.sessions = {}
        self.session_timeout = 3600  # 1 hour
        self.session_file = Path("temp_storage/sessions.json")
        self._load_sessions()
    
    def _load_sessions(self):
        """Load sessions from file."""
        try:
            if self.session_file.exists():
                import json
                with open(self.session_file, 'r') as f:
                    self.sessions = json.load(f)
                logger.info(f"Loaded {len(self.sessions)} sessions from disk")
                print(f"💾 Loaded {len(self.sessions)} sessions from persistence")
        except Exception as e:
            logger.warning(f"Could not load sessions: {str(e)}")
            self.sessions = {}
    
    def _save_sessions(self):
        """Save sessions to file."""
        try:
            import json
            self.session_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.session_file, 'w') as f:
                json.dump(self.sessions, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save sessions: {str(e)}")
    
    def create_session(self) -> str:
        """
        Create new session.
        
        Returns:
            Session ID
        """
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        
        self.sessions[session_id] = {
            'session_id': session_id,
            'created_at': time.time(),
            'status': 'active',
            'steps': [],
            'data': {}
        }
        
        self._save_sessions()  # Persist to disk
        logger.info(f"Created session: {session_id}")
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data."""
        return self.sessions.get(session_id)
    
    def update_session(self, session_id: str, step: str, data: Dict[str, Any]):
        """
        Update session with step completion.
        
        Args:
            session_id: Session ID
            step: Step name
            data: Step data
        """
        if session_id in self.sessions:
            self.sessions[session_id]['steps'].append({
                'step': step,
                'timestamp': time.time(),
                'data': data
            })
            self.sessions[session_id]['data'].update(data)
            self._save_sessions()  # Persist to disk
    
    def close_session(self, session_id: str):
        """Mark session as complete."""
        if session_id in self.sessions:
            self.sessions[session_id]['status'] = 'completed'
            self._save_sessions()  # Persist to disk
            logger.info(f"Closed session: {session_id}")
    
    def cleanup_old_sessions(self):
        """Remove expired sessions."""
        current_time = time.time()
        expired = []
        
        for sid, session in self.sessions.items():
            age = current_time - session['created_at']
            if age > self.session_timeout:
                expired.append(sid)
        
        for sid in expired:
            del self.sessions[sid]
        
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")


class Orchestrator:
    """Main orchestrator for invoice validation workflow."""
    
    def __init__(self):
        self.session_manager = SessionManager()
        self.extraction_agent = extraction_agent
        self.excel_agent = excel_agent
        self.policy_agent = policy_agent
    
    async def process_validation(
        self,
        invoice_id: str,
        proposal_id: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute full validation workflow.
        
        Args:
            invoice_id: Invoice file ID
            proposal_id: Proposal Excel file ID
            session_id: Optional session ID to use (creates new if not provided)
            
        Returns:
            Validation result
            
        Raises:
            Exception: If workflow fails
        """
        # Use provided session_id or create new one
        if session_id is None:
            session_id = self.session_manager.create_session()
            print(f"🆕 Created NEW session: {session_id}")
        else:
            # Ensure session exists in manager
            if session_id not in self.session_manager.sessions:
                self.session_manager.sessions[session_id] = {
                    'session_id': session_id,
                    'created_at': time.time(),
                    'status': 'active',
                    'steps': [],
                    'data': {}
                }
                self.session_manager._save_sessions()  # Persist to disk
                print(f"📝 Registered existing session: {session_id}")
                logger.info(f"Registered existing session: {session_id}")
            else:
                print(f"♻️  Reusing existing session: {session_id}")
        
        try:
            print(f"\n{'='*80}")
            print(f"🚀 STARTING VALIDATION WORKFLOW")
            print(f"{'='*80}")
            print(f"Session ID: {session_id}")
            print(f"Invoice ID: {invoice_id}")
            print(f"Proposal ID: {proposal_id}")
            logger.info(f"[{session_id}] Starting validation: invoice={invoice_id}, proposal={proposal_id}")
            
            # Step 1: Load files
            print(f"\n📁 STEP 1: Loading Files...")
            invoice_path, proposal_path = await self._load_files(
                invoice_id, proposal_id, session_id
            )
            print(f"✅ Files loaded successfully")
            print(f"   Invoice: {invoice_path.name}")
            print(f"   Proposal: {proposal_path.name}")
            
            # Step 2: Extract invoice data
            print(f"\n🔍 STEP 2: Extracting Invoice Data...")
            print(f"   Using Vision Model: gemma3:27b")
            print(f"   Processing: {invoice_path.name}")
            extracted_data = await self._extract_invoice(invoice_path, session_id)
            print(f"✅ Extraction completed!")
            print(f"   Passenger: {extracted_data.get('passenger_name', 'unknown')}")
            print(f"   From: {extracted_data.get('origin', 'unknown')}")
            print(f"   To: {extracted_data.get('destination', 'unknown')}")
            print(f"   Date: {extracted_data.get('travel_date', 'unknown')}")
            print(f"   Fare: ₹{extracted_data.get('fare', 0.0):.2f}")
            print(f"   Confidence: {extracted_data.get('confidence', 0.0)*100:.1f}%")
            
            # Step 3: Match employee
            print(f"\n👤 STEP 3: Matching Employee...")
            print(f"   Searching for: {extracted_data['passenger_name']}")
            employee_data = await self._match_employee(
                proposal_path, extracted_data['passenger_name'], session_id
            )
            print(f"✅ Employee matched!")
            print(f"   Name: {employee_data.get('name', 'unknown')}")
            print(f"   Level: {employee_data.get('employee_level', 'unknown')}")
            print(f"   Fare Limit: ₹{employee_data.get('fare_limit', 0.0):,.2f}")
            
            # Step 4: Validate against policy
            print(f"\n📋 STEP 4: Validating Against Policy...")
            print(f"   Running RAG-based policy check...")
            validation_result = await self._validate_policy(
                extracted_data, employee_data, session_id
            )
            print(f"✅ Validation completed!")
            print(f"   Status: {validation_result.get('validation_status', 'unknown').upper()}")
            
            # Step 5: Build final response
            print(f"\n📊 STEP 5: Building Final Response...")
            final_result = self._build_final_response(
                extracted_data, employee_data, validation_result, session_id
            )
            print(f"✅ Response built successfully!")
            
            # Close session
            self.session_manager.close_session(session_id)
            
            print(f"\n{'='*80}")
            print(f"✅ VALIDATION WORKFLOW COMPLETED")
            print(f"{'='*80}")
            print(f"Final Status: {final_result['validation_status'].upper()}")
            print(f"{'='*80}\n")
            
            logger.info(f"[{session_id}] Validation complete: {final_result['validation_status']}")
            
            return final_result
            
        except Exception as e:
            print(f"\n{'='*80}")
            print(f"❌ VALIDATION WORKFLOW FAILED")
            print(f"{'='*80}")
            print(f"Error: {str(e)}")
            print(f"{'='*80}\n")
            logger.error(f"[{session_id}] Validation workflow failed: {str(e)}", exc_info=True)
            
            # Build error response
            error_result = {
                'name': 'unknown',
                'from': 'unknown',
                'to': 'unknown',
                'date': 'unknown',
                'fare': 0.0,
                'confidence': 0.0,
                'validation_status': 'rejected',
                'remarks': f'Validation failed: {str(e)}',
                'session_id': session_id,
                'error': str(e)
            }
            
            return error_result
    
    async def _load_files(
        self,
        invoice_id: str,
        proposal_id: str,
        session_id: str
    ) -> tuple[Path, Path]:
        """
        Load invoice and proposal files.
        
        Returns:
            Tuple of (invoice_path, proposal_path)
        """
        try:
            logger.info(f"[{session_id}] Loading files...")
            print(f"   Resolving invoice path for ID: {invoice_id}")
            
            # Get file paths
            invoice_path = file_storage.get_invoice_path(invoice_id)
            proposal_path = file_storage.get_proposal_path(proposal_id)
            
            print(f"   Resolved invoice path: {invoice_path}")
            print(f"   Resolved proposal path: {proposal_path}")
            
            # Verify files exist
            if not invoice_path.exists():
                raise FileNotFoundError(f"Invoice file not found: {invoice_id}")
            
            if not proposal_path.exists():
                raise FileNotFoundError(f"Proposal file not found: {proposal_id}")
            
            print(f"   Invoice file size: {invoice_path.stat().st_size} bytes")
            print(f"   Proposal file size: {proposal_path.stat().st_size} bytes")
            
            logger.info(f"[{session_id}] Files loaded successfully")
            
            self.session_manager.update_session(session_id, 'load_files', {
                'invoice_path': str(invoice_path),
                'proposal_path': str(proposal_path)
            })
            
            return invoice_path, proposal_path
            
        except Exception as e:
            print(f"   ❌ Error loading files: {str(e)}")
            logger.error(f"[{session_id}] File loading failed: {str(e)}")
            raise Exception(f"Failed to load files: {str(e)}")
    
    async def _extract_invoice(
        self,
        invoice_path: Path,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Extract data from invoice.
        
        Returns:
            Extracted invoice data
        """
        try:
            logger.info(f"[{session_id}] Extracting invoice data...")
            print(f"   Calling extraction agent with retry capability...")
            
            # Call extraction agent with retry
            extracted_data = await self.extraction_agent.extract_with_fallback(
                invoice_path, session_id, retry_count=2
            )
            
            print(f"   Extraction agent returned data")
            logger.info(f"[{session_id}] Extraction complete (confidence: {extracted_data['confidence']:.2f})")
            
            self.session_manager.update_session(session_id, 'extract_invoice', {
                'extracted_data': extracted_data
            })
            
            return extracted_data
            
        except Exception as e:
            print(f"   ❌ Extraction error: {str(e)}")
            logger.error(f"[{session_id}] Invoice extraction failed: {str(e)}")
            raise Exception(f"Invoice extraction failed: {str(e)}")
    
    async def _match_employee(
        self,
        proposal_path: Path,
        passenger_name: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Match passenger with employee in proposal.
        
        Returns:
            Employee match data
        """
        try:
            logger.info(f"[{session_id}] Matching employee: {passenger_name}")
            
            # Call Excel agent
            employee_data = await self.excel_agent.find_employee_match(
                proposal_path, passenger_name, session_id
            )
            
            if employee_data['match_found']:
                logger.info(f"[{session_id}] Employee matched: {employee_data['employee_name']} "
                          f"(confidence: {employee_data['match_confidence']:.2f})")
            else:
                logger.warning(f"[{session_id}] Employee not matched")
            
            self.session_manager.update_session(session_id, 'match_employee', {
                'employee_data': employee_data
            })
            
            return employee_data
            
        except Exception as e:
            logger.error(f"[{session_id}] Employee matching failed: {str(e)}")
            raise Exception(f"Employee matching failed: {str(e)}")
    
    async def _validate_policy(
        self,
        extracted_data: Dict[str, Any],
        employee_data: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """
        Validate against business rules.
        
        Returns:
            Validation result
        """
        try:
            logger.info(f"[{session_id}] Validating against policy...")
            
            # Call policy agent
            validation_result = await self.policy_agent.validate_invoice(
                extracted_data, employee_data, session_id
            )
            
            logger.info(f"[{session_id}] Policy validation complete: {validation_result['validation_status']}")
            
            self.session_manager.update_session(session_id, 'validate_policy', {
                'validation_result': validation_result
            })
            
            return validation_result
            
        except Exception as e:
            logger.error(f"[{session_id}] Policy validation failed: {str(e)}")
            raise Exception(f"Policy validation failed: {str(e)}")
    
    def _build_final_response(
        self,
        extracted_data: Dict[str, Any],
        employee_data: Dict[str, Any],
        validation_result: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """
        Build final response in required format.
        
        Returns:
            Final validation response
        """
        try:
            # Calculate overall confidence
            # Combine extraction, matching, and validation confidences
            extraction_conf = extracted_data.get('confidence', 0.0)
            match_conf = employee_data.get('match_confidence', 0.0)
            validation_conf = validation_result.get('confidence', 0.0)
            
            # Weighted average
            overall_confidence = (extraction_conf * 0.3 + match_conf * 0.3 + validation_conf * 0.4)
            
            # Build response
            response = {
                'name': extracted_data.get('passenger_name', 'unknown'),
                'from': extracted_data.get('origin', 'unknown'),
                'to': extracted_data.get('destination', 'unknown'),
                'date': extracted_data.get('travel_date', 'unknown'),
                'fare': float(extracted_data.get('fare', 0.0)),
                'confidence': round(overall_confidence, 2),
                'validation_status': validation_result.get('validation_status', 'rejected'),
                'remarks': validation_result.get('remarks', 'Validation completed'),
                'session_id': session_id
            }
            
            logger.info(f"[{session_id}] Final response built")
            logger.debug(f"[{session_id}] Response: {response}")
            
            return response
            
        except Exception as e:
            logger.error(f"[{session_id}] Failed to build response: {str(e)}")
            raise Exception(f"Failed to build final response: {str(e)}")
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information for debugging."""
        return self.session_manager.get_session(session_id)
    
    def cleanup_sessions(self):
        """Cleanup old sessions."""
        self.session_manager.cleanup_old_sessions()
    
    async def chat_with_context(
        self,
        session_id: str,
        user_question: str
    ) -> Dict[str, Any]:
        """
        Chat with orchestrator about session data.
        User can ask questions about validation results, policies, extracted data, etc.
        
        Args:
            session_id: Session ID to get context from
            user_question: User's question
            
        Returns:
            Dict with answer and metadata
            
        Raises:
            Exception: If session not found or chat fails
        """
        try:
            print(f"\n{'='*80}")
            print(f"💬 USER CHAT REQUEST")
            print(f"{'='*80}")
            print(f"Session ID: {session_id}")
            print(f"Question: {user_question}")
            logger.info(f"[{session_id}] Chat request: {user_question}")
            
            # DEBUG: Check available sessions
            print(f"\n🔍 DEBUG: Checking session availability...")
            print(f"   Total sessions in manager: {len(self.session_manager.sessions)}")
            print(f"   Available session IDs: {list(self.session_manager.sessions.keys())}")
            print(f"   Looking for: {session_id}")
            
            # Get session data
            session = self.session_manager.get_session(session_id)
            
            if not session:
                print(f"   ❌ Session {session_id} NOT FOUND!")
                print(f"   Available sessions: {list(self.session_manager.sessions.keys())}")
                raise Exception(f"Session {session_id} not found. Please process validation first.")
            
            print(f"   ✅ Session found! Status: {session.get('status')}")
            
            # Extract all available data from session
            session_data = session.get('data', {})
            
            # Build context from session
            context_parts = []
            
            # Extracted data
            if 'extracted_data' in session_data:
                extracted = session_data['extracted_data']
                context_parts.append(f"""
EXTRACTED INVOICE DATA:
- Passenger Name: {extracted.get('passenger_name', 'N/A')}
- Origin: {extracted.get('origin', 'N/A')}
- Destination: {extracted.get('destination', 'N/A')}
- Travel Date: {extracted.get('travel_date', 'N/A')}
- Fare: ₹{extracted.get('fare', 0.0)}
- Extraction Confidence: {extracted.get('confidence', 0.0)*100:.1f}%
""")
            
            # Employee data
            if 'employee_data' in session_data:
                employee = session_data['employee_data']
                context_parts.append(f"""
EMPLOYEE DETAILS:
- Name: {employee.get('name', 'N/A')}
- Level: {employee.get('employee_level', 'N/A')}
- Fare Limit: ₹{employee.get('fare_limit', 0.0):,.2f}
""")
            
            # Validation result
            if 'validation_result' in session_data:
                validation = session_data['validation_result']
                context_parts.append(f"""
VALIDATION RESULT:
- Status: {validation.get('validation_status', 'N/A').upper()}
- Remarks: {validation.get('remarks', 'N/A')}
""")
                
                # Policy rules applied (check both possible field names)
                rules = validation.get('policy_rules_applied') or validation.get('rules_applied')
                if rules:
                    # Handle rules that might be strings or have other formats
                    rule_list = []
                    for rule in rules:
                        if isinstance(rule, str):
                            rule_list.append(f"- {rule}")
                        else:
                            rule_list.append(f"- {str(rule)}")
                    
                    context_parts.append(f"""
POLICY RULES APPLIED:
{chr(10).join(rule_list)}
""")
                
                # Violations
                if validation.get('violations'):
                    violations = validation['violations']
                    # Handle violations that might be strings or dicts
                    violation_list = []
                    for v in violations:
                        if isinstance(v, dict):
                            violation_list.append(f"- {v.get('description', str(v))}")
                        else:
                            violation_list.append(f"- {v}")
                    
                    context_parts.append(f"""
POLICY VIOLATIONS:
{chr(10).join(violation_list)}
""")
            
            # Combine context
            full_context = "\n".join(context_parts)
            
            print(f"\n📋 Session Context Loaded:")
            print(f"   - Has extracted data: {'extracted_data' in session_data}")
            print(f"   - Has employee data: {'employee_data' in session_data}")
            print(f"   - Has validation result: {'validation_result' in session_data}")
            
            # Build chat prompt
            system_prompt = """You are an AI assistant helping users understand their travel invoice validation results.

You have access to the complete session data including:
- Extracted invoice information (passenger, route, date, fare)
- Employee details (name, level, fare limits)
- Validation results (approved/rejected status)
- Policy rules that were applied
- Any policy violations found

Answer the user's question clearly and concisely based on the available data.
If the data needed to answer the question is not available, say so politely.

Be helpful, accurate, and reference specific data points when answering."""

            user_prompt = f"""Here is the session data:

{full_context}

User's Question: {user_question}

Please answer based on the above information."""

            # Call LLM
            from src.agents.llm_client import ollama_client
            
            print(f"\n🤖 Calling LLM to generate answer...")
            
            response = await ollama_client.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.3  # Lower temperature for factual responses
            )
            
            answer = response.get('response', '').strip()
            
            print(f"✅ Answer generated!")
            print(f"   Length: {len(answer)} characters")
            print(f"{'='*80}\n")
            
            logger.info(f"[{session_id}] Chat response generated")
            
            return {
                'session_id': session_id,
                'question': user_question,
                'answer': answer,
                'has_context': bool(context_parts),
                'context_items': len(context_parts)
            }
            
        except Exception as e:
            print(f"❌ Chat error: {str(e)}")
            print(f"{'='*80}\n")
            logger.error(f"[{session_id}] Chat failed: {str(e)}", exc_info=True)
            raise Exception(f"Chat request failed: {str(e)}")


# Singleton instance
orchestrator = Orchestrator()
