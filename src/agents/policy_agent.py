"""
Policy Agent - Validates invoices against business rules using RAG + LLM.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from src.agents.llm_client import ollama_client
from src.agents.rules_rag.query_vectorstore import rules_retriever
from src.config.settings import settings

logger = logging.getLogger(__name__)


class PolicyAgent:
    """Agent for policy-based validation using RAG and LLM."""
    
    def __init__(self):
        self.llm_client = ollama_client
        self.rules_retriever = rules_retriever
    
    async def validate_invoice(
        self,
        extracted_data: Dict[str, Any],
        employee_data: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate invoice against business rules.
        
        Args:
            extracted_data: Invoice data from extraction agent
            employee_data: Employee match data from Excel agent
            session_id: Session identifier
            
        Returns:
            Dict with:
                - validation_status: str (approved/rejected)
                - confidence: float (0-1)
                - remarks: str (explanation)
                - rules_applied: List[str]
                - violations: List[str]
                
        Raises:
            Exception: If validation fails
        """
        try:
            log_prefix = f"[{session_id}] " if session_id else ""
            logger.info(f"{log_prefix}Validating invoice for {extracted_data.get('passenger_name')}")
            
            # Build validation context
            validation_context = self._build_validation_context(extracted_data, employee_data)
            
            # Retrieve relevant rules
            relevant_rules = self._retrieve_relevant_rules(validation_context)
            
            logger.info(f"{log_prefix}Retrieved {len(relevant_rules)} relevant rules")
            
            # Perform rule-based checks first
            rule_checks = self._check_basic_rules(extracted_data, employee_data)
            
            # If basic checks fail badly, can reject immediately
            if rule_checks['critical_failure']:
                logger.warning(f"{log_prefix}Critical rule violation detected")
                return {
                    'validation_status': 'rejected',
                    'confidence': 0.95,
                    'remarks': rule_checks['failure_reason'],
                    'rules_applied': rule_checks['rules_checked'],
                    'violations': rule_checks['violations']
                }
            
            # Use LLM for complex validation
            llm_result = await self._llm_validation(
                extracted_data=extracted_data,
                employee_data=employee_data,
                relevant_rules=relevant_rules,
                rule_checks=rule_checks,
                session_id=session_id
            )
            
            # Combine rule-based and LLM results
            final_result = self._combine_validation_results(rule_checks, llm_result)
            
            logger.info(f"{log_prefix}Validation complete: {final_result['validation_status']} "
                       f"(confidence: {final_result['confidence']:.2f})")
            
            return final_result
            
        except Exception as e:
            logger.error(f"{log_prefix}Validation failed: {str(e)}", exc_info=True)
            raise Exception(f"Policy validation failed: {str(e)}")
    
    def _build_validation_context(
        self,
        extracted_data: Dict[str, Any],
        employee_data: Dict[str, Any]
    ) -> str:
        """
        Build context string for rule retrieval.
        
        Args:
            extracted_data: Invoice data
            employee_data: Employee data
            
        Returns:
            Context string for RAG
        """
        context = f"""
Travel invoice validation context:
- Employee Level: {employee_data.get('employee_level', 'unknown')}
- Fare Amount: {extracted_data.get('fare', 0.0)}
- Fare Limit: {employee_data.get('fare_limit', 0.0)}
- Travel Route: {extracted_data.get('origin')} to {extracted_data.get('destination')}
- Match Confidence: {employee_data.get('match_confidence', 0.0)}
- Extraction Confidence: {extracted_data.get('confidence', 0.0)}
"""
        return context.strip()
    
    def _retrieve_relevant_rules(self, context: str) -> List[str]:
        """
        Retrieve relevant business rules from vector store.
        
        Args:
            context: Validation context
            
        Returns:
            List of relevant rule texts
        """
        try:
            # Query vector store
            rules = self.rules_retriever.retrieve_rules(context, top_k=settings.TOP_K_RULES)
            
            if not rules:
                logger.warning("No rules retrieved from vector store, using fallback")
                # Return basic fallback rules
                rules = [
                    "Fare must not exceed the employee's fare limit by more than 10%",
                    "All required invoice fields must be present",
                    "Employee must be found in the proposal"
                ]
            
            return rules
            
        except Exception as e:
            logger.error(f"Rule retrieval failed: {str(e)}")
            # Return minimal fallback rules
            return ["Validate that fare is within policy limits"]
    
    def _check_basic_rules(
        self,
        extracted_data: Dict[str, Any],
        employee_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform basic rule-based checks.
        
        Args:
            extracted_data: Invoice data
            employee_data: Employee data
            
        Returns:
            Dict with check results
        """
        violations = []
        rules_checked = []
        critical_failure = False
        failure_reason = ""
        
        # Check 1: Employee must be found
        rules_checked.append("Employee identification")
        if not employee_data.get('match_found', False):
            violations.append("Employee not found in proposal")
            critical_failure = True
            failure_reason = "Employee not found in travel proposal"
        
        # Check 2: Required invoice fields
        rules_checked.append("Required invoice fields")
        missing_fields = []
        for field in ['passenger_name', 'origin', 'destination', 'fare']:
            value = extracted_data.get(field)
            if not value or value == 'unknown' or value == 0.0:
                missing_fields.append(field)
        
        if missing_fields:
            violations.append(f"Missing invoice fields: {', '.join(missing_fields)}")
            if len(missing_fields) >= 3:
                critical_failure = True
                failure_reason = f"Too many missing fields: {', '.join(missing_fields)}"
        
        # Check 3: Fare limit
        rules_checked.append("Fare limit validation")
        fare = extracted_data.get('fare', 0.0)
        fare_limit = employee_data.get('fare_limit', 0.0)
        
        if fare_limit > 0:
            overage_pct = ((fare - fare_limit) / fare_limit) * 100
            
            if overage_pct > 10:
                violations.append(f"Fare exceeds limit by {overage_pct:.1f}%")
                critical_failure = True
                failure_reason = f"Fare ₹{fare:.2f} exceeds limit ₹{fare_limit:.2f} by {overage_pct:.1f}%"
            elif overage_pct > 5:
                violations.append(f"Fare slightly exceeds limit by {overage_pct:.1f}%")
        
        # Check 4: Extraction confidence
        rules_checked.append("Data quality check")
        extraction_conf = extracted_data.get('confidence', 0.0)
        if extraction_conf < 0.5:
            violations.append(f"Low extraction confidence: {extraction_conf:.2f}")
        
        # Check 5: Match confidence
        rules_checked.append("Employee match quality")
        match_conf = employee_data.get('match_confidence', 0.0)
        if match_conf < 0.7:
            violations.append(f"Low employee match confidence: {match_conf:.2f}")
        
        return {
            'violations': violations,
            'rules_checked': rules_checked,
            'critical_failure': critical_failure,
            'failure_reason': failure_reason,
            'fare_within_limit': fare <= fare_limit if fare_limit > 0 else None
        }
    
    async def _llm_validation(
        self,
        extracted_data: Dict[str, Any],
        employee_data: Dict[str, Any],
        relevant_rules: List[str],
        rule_checks: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Use LLM for nuanced validation decision.
        
        Args:
            extracted_data: Invoice data
            employee_data: Employee data
            relevant_rules: Retrieved business rules
            rule_checks: Results from basic rule checks
            session_id: Session ID
            
        Returns:
            LLM validation result
        """
        try:
            # Build prompt
            prompt = self._create_validation_prompt(
                extracted_data, employee_data, relevant_rules, rule_checks
            )
            
            system_prompt = """You are a travel expense validation expert.
Analyze the invoice data, employee information, and business rules to make a validation decision.
You must respond with valid JSON only."""
            
            # Call LLM
            log_prefix = f"[{session_id}] " if session_id else ""
            logger.info(f"{log_prefix}Calling LLM for validation decision...")
            
            response = await self.llm_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.2,
                json_mode=True
            )
            
            # Parse response
            raw_response = response.get('response', '').strip()
            logger.debug(f"{log_prefix}LLM validation response: {raw_response[:500]}")
            
            # Extract JSON
            result = self._parse_llm_validation_response(raw_response)
            
            return result
            
        except Exception as e:
            logger.error(f"LLM validation failed: {str(e)}", exc_info=True)
            # Return conservative fallback
            return {
                'validation_status': 'rejected',
                'confidence': 0.3,
                'remarks': f"Validation failed due to system error: {str(e)}",
                'llm_error': True
            }
    
    def _create_validation_prompt(
        self,
        extracted_data: Dict[str, Any],
        employee_data: Dict[str, Any],
        relevant_rules: List[str],
        rule_checks: Dict[str, Any]
    ) -> str:
        """Create prompt for LLM validation."""
        
        rules_text = "\n".join([f"- {rule}" for rule in relevant_rules])
        violations_text = "\n".join([f"- {v}" for v in rule_checks['violations']])
        
        prompt = f"""Analyze this travel invoice validation case:

INVOICE DATA:
- Passenger: {extracted_data.get('passenger_name')}
- Route: {extracted_data.get('origin')} → {extracted_data.get('destination')}
- Date: {extracted_data.get('travel_date')}
- Fare: ₹{extracted_data.get('fare', 0.0):.2f}
- Extraction Confidence: {extracted_data.get('confidence', 0.0):.2f}

EMPLOYEE DATA:
- Match Found: {employee_data.get('match_found', False)}
- Employee Name: {employee_data.get('employee_name')}
- Employee Level: {employee_data.get('employee_level')}
- Fare Limit: ₹{employee_data.get('fare_limit', 0.0):.2f}
- Match Confidence: {employee_data.get('match_confidence', 0.0):.2f}

RELEVANT BUSINESS RULES:
{rules_text}

AUTOMATED CHECKS:
Violations detected:
{violations_text if rule_checks['violations'] else '- None'}

TASK:
Based on the above information, determine if this invoice should be APPROVED or REJECTED.

Consider:
1. Is the fare within acceptable limits for the employee level?
2. Are all required fields present and valid?
3. Is the employee match reliable?
4. Are there any policy violations?

Respond with ONLY a JSON object in this format:
{{
    "validation_status": "approved" or "rejected",
    "confidence": 0.85,
    "remarks": "concise explanation of decision"
}}

Your decision:"""
        
        return prompt
    
    def _parse_llm_validation_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM validation response."""
        try:
            # Extract JSON
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise Exception("No JSON found in response")
            
            json_str = response_text[json_start:json_end]
            data = json.loads(json_str)
            
            # Normalize status
            status = str(data.get('validation_status', 'rejected')).lower()
            if status not in ['approved', 'rejected']:
                status = 'rejected'
            
            return {
                'validation_status': status,
                'confidence': float(data.get('confidence', 0.5)),
                'remarks': str(data.get('remarks', 'Validation decision made'))
            }
            
        except Exception as e:
            logger.error(f"Failed to parse LLM validation response: {str(e)}")
            return {
                'validation_status': 'rejected',
                'confidence': 0.3,
                'remarks': 'Failed to parse validation decision'
            }
    
    def _combine_validation_results(
        self,
        rule_checks: Dict[str, Any],
        llm_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Combine rule-based and LLM validation results.
        
        Args:
            rule_checks: Basic rule check results
            llm_result: LLM validation result
            
        Returns:
            Final validation result
        """
        # If critical failure, override LLM
        if rule_checks['critical_failure']:
            status = 'rejected'
            confidence = 0.95
            remarks = rule_checks['failure_reason']
        else:
            status = llm_result['validation_status']
            confidence = llm_result['confidence']
            remarks = llm_result['remarks']
            
            # Adjust confidence based on violations
            if rule_checks['violations']:
                confidence *= 0.9
        
        return {
            'validation_status': status,
            'confidence': min(confidence, 1.0),
            'remarks': remarks,
            'rules_applied': rule_checks['rules_checked'],
            'violations': rule_checks['violations']
        }


# Singleton instance
policy_agent = PolicyAgent()
