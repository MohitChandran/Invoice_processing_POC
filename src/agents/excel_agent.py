"""
Excel Agent - Matches invoice data with employee proposal.
Handles fuzzy matching and employee data extraction.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from fuzzywuzzy import fuzz, process
import pandas as pd
from src.services.excel_utils import excel_utils
from src.config.settings import settings

logger = logging.getLogger(__name__)


class ExcelAgent:
    """Agent for matching invoice data with Excel proposal."""
    
    # Valid relations for approval
    VALID_RELATIONS = [
        'self',      # Primary employee
        'wife',
        'husband', 
        'son',
        'daughter',
        'mother',
        'father'
    ]
    
    def __init__(self):
        self.fuzzy_threshold = settings.FUZZY_MATCH_THRESHOLD
    
    async def find_employee_match(
        self,
        excel_path: Path,
        passenger_name: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Find matching employee in Excel proposal.
        
        Args:
            excel_path: Path to Excel file
            passenger_name: Name to match
            session_id: Session identifier
            
        Returns:
            Dict with:
                - match_found: bool
                - employee_name: str
                - employee_level: str
                - fare_limit: float
                - match_confidence: float (0-1)
                - match_type: str (exact/fuzzy/none)
                - all_candidates: List[Dict] (if multiple matches)
                
        Raises:
            Exception: If Excel processing fails
        """
        try:
            log_prefix = f"[{session_id}] " if session_id else ""
            logger.info(f"{log_prefix}Matching employee: {passenger_name}")
            
            # Load and validate Excel
            df = excel_utils.load_excel(excel_path)
            
            # Validate required columns
            required_cols = ['name']  # Minimum required
            excel_utils.validate_columns(df, required_cols)
            
            # Normalize data
            df = excel_utils.normalize_employee_data(df)
            
            # Try exact match first
            exact_match = excel_utils.get_employee_by_name(df, passenger_name)
            
            if exact_match:
                logger.info(f"{log_prefix}Found exact match")
                
                # Always build the match result first to extract all fields
                result = self._build_match_result(
                    df=df,
                    matched_row=exact_match,
                    match_type='exact',
                    confidence=1.0
                )
                
                # The _build_match_result already adds validation_error and auto_reject if needed
                return result
            
            # Try fuzzy matching
            logger.info(f"{log_prefix}Exact match not found, trying fuzzy match...")
            fuzzy_result = await self._fuzzy_match_employee(df, passenger_name)
            
            if fuzzy_result['match_found']:
                logger.info(f"{log_prefix}Found fuzzy match: {fuzzy_result['employee_name']} "
                          f"(confidence: {fuzzy_result['match_confidence']:.2f})")
                
                # Check if fuzzy result has auto_reject flag
                if fuzzy_result.get('auto_reject'):
                    logger.warning(f"{log_prefix}Fuzzy match rejected due to validation: {fuzzy_result.get('validation_error')}")
                
                return fuzzy_result
            
            # No match found
            logger.warning(f"{log_prefix}No match found for: {passenger_name}")
            
            return {
                'match_found': False,
                'employee_name': passenger_name,
                'employee_level': 'unknown',
                'fare_limit': 0.0,
                'match_confidence': 0.0,
                'match_type': 'none',
                'all_candidates': [],
                'error': 'No matching employee found in proposal'
            }
            
        except Exception as e:
            logger.error(f"{log_prefix}Employee matching failed: {str(e)}", exc_info=True)
            raise Exception(f"Failed to match employee: {str(e)}")
    
    async def _fuzzy_match_employee(
        self,
        df: pd.DataFrame,
        target_name: str
    ) -> Dict[str, Any]:
        """
        Perform fuzzy matching on employee names.
        
        Args:
            df: Employee DataFrame
            target_name: Name to match
            
        Returns:
            Match result dict
        """
        try:
            # Get all names
            all_names = excel_utils.get_all_names(df)
            
            if not all_names:
                logger.warning("No names found in Excel")
                return {
                    'match_found': False,
                    'employee_name': target_name,
                    'employee_level': 'unknown',
                    'fare_limit': 0.0,
                    'match_confidence': 0.0,
                    'match_type': 'none',
                    'all_candidates': []
                }
            
            # Normalize target name and all names to lowercase for case-insensitive matching
            target_name_lower = target_name.lower()
            all_names_lower = [name.lower() for name in all_names]
            
            # Perform fuzzy matching on lowercase names
            matches = process.extract(target_name_lower, all_names_lower, scorer=fuzz.token_sort_ratio, limit=5)
            
            logger.debug(f"Fuzzy matches: {matches}")
            
            # Check best match (map back to original name)
            best_match_name_lower, best_score = matches[0]
            # Find the original name from the lowercase match
            best_match_index = all_names_lower.index(best_match_name_lower)
            best_match_name = all_names[best_match_index]
            
            if best_score >= self.fuzzy_threshold:
                # Good match found
                matched_row = excel_utils.get_employee_by_name(df, best_match_name)
                
                if matched_row:
                    # Check for ambiguous matches
                    ambiguous = False
                    candidates = []
                    
                    for match_name_lower, score in matches:
                        if score >= self.fuzzy_threshold:
                            # Map back to original name
                            match_index = all_names_lower.index(match_name_lower)
                            original_name = all_names[match_index]
                            candidates.append({
                                'name': original_name,
                                'score': score / 100.0
                            })
                    
                    if len(candidates) > 1:
                        ambiguous = True
                        logger.warning(f"Ambiguous match: {len(candidates)} candidates found")
                    
                    result = self._build_match_result(
                        df=df,
                        matched_row=matched_row,
                        match_type='fuzzy',
                        confidence=best_score / 100.0
                    )
                    
                    result['all_candidates'] = candidates
                    result['ambiguous'] = ambiguous
                    
                    return result
            
            # No good match - map lowercase names back to original
            candidates_list = []
            for match_name_lower, score in matches[:3]:
                match_index = all_names_lower.index(match_name_lower)
                original_name = all_names[match_index]
                candidates_list.append({'name': original_name, 'score': score / 100.0})
            
            return {
                'match_found': False,
                'employee_name': target_name,
                'employee_level': 'unknown',
                'fare_limit': 0.0,
                'match_confidence': best_score / 100.0,
                'match_type': 'none',
                'all_candidates': candidates_list
            }
            
        except Exception as e:
            logger.error(f"Fuzzy matching failed: {str(e)}", exc_info=True)
            raise
    
    def _build_match_result(
        self,
        df: pd.DataFrame,
        matched_row: Dict[str, Any],
        match_type: str,
        confidence: float
    ) -> Dict[str, Any]:
        """
        Build standardized match result.
        
        Args:
            df: Source DataFrame
            matched_row: Matched row data
            match_type: Type of match (exact/fuzzy)
            confidence: Match confidence
            
        Returns:
            Standardized result dict
        """
        try:
            # Extract employee name
            name_col = None
            for col in df.columns:
                if 'name' in col:
                    name_col = col
                    break
            
            employee_name = str(matched_row.get(name_col, 'unknown'))
            
            # Extract employee level
            level_col = None
            for col in df.columns:
                if 'level' in col:
                    level_col = col
                    break
            
            employee_level = 'unknown'
            if level_col and matched_row.get(level_col):
                employee_level = str(matched_row[level_col]).strip().lower()
            
            # Extract fare limit
            limit_col = None
            for col in df.columns:
                if 'fare' in col and 'limit' in col:
                    limit_col = col
                    break
                elif 'limit' in col:
                    limit_col = col
                    break
            
            fare_limit = 0.0
            if limit_col:
                try:
                    fare_limit = float(matched_row.get(limit_col, 0.0))
                except (ValueError, TypeError):
                    logger.warning(f"Could not parse fare limit: {matched_row.get(limit_col)}")
                    fare_limit = 0.0
            
            # Handle missing fare limit
            if fare_limit == 0.0 or pd.isna(fare_limit):
                logger.warning(f"Fare limit missing or zero for {employee_name}, using fallback")
                # Use fallback based on level
                fare_limit = self._get_default_fare_limit(employee_level)
            
            # Extract relation_member (person name)
            relation_member_col = None
            for col in df.columns:
                if 'relation_member' in col or 'member_name' in col or 'dependent_name' in col:
                    relation_member_col = col
                    break
            
            relation_member = 'N/A'
            if relation_member_col and matched_row.get(relation_member_col):
                relation_member = str(matched_row[relation_member_col]).strip()
            
            # Extract relation
            relation_col = None
            for col in df.columns:
                if 'relation' in col and 'member' not in col:
                    relation_col = col
                    break
            
            relation = 'N/A'
            if relation_col and matched_row.get(relation_col):
                relation = str(matched_row[relation_col]).strip()
            
            # Extract status
            status_col = None
            for col in df.columns:
                if 'status' in col:
                    status_col = col
                    break
            
            status = 'N/A'
            if status_col and matched_row.get(status_col):
                status = str(matched_row[status_col]).strip()
            
            # Extract travel details from Excel (NEW FIELDS)
            # Extract 'from' location
            from_col = None
            for col in df.columns:
                if col in ['from', 'origin', 'departure', 'source']:
                    from_col = col
                    break
            
            excel_from = 'N/A'
            if from_col and matched_row.get(from_col):
                excel_from = str(matched_row[from_col]).strip()
            
            # Extract 'to' location
            to_col = None
            for col in df.columns:
                if col in ['to', 'destination', 'arrival']:
                    to_col = col
                    break
            
            excel_to = 'N/A'
            if to_col and matched_row.get(to_col):
                excel_to = str(matched_row[to_col]).strip()
            
            # Extract fare from Excel
            fare_col = None
            for col in df.columns:
                if col == 'fare' or 'fare' in col and 'limit' not in col:
                    fare_col = col
                    break
            
            excel_fare = 0.0
            if fare_col:
                try:
                    excel_fare = float(matched_row.get(fare_col, 0.0))
                except (ValueError, TypeError):
                    logger.warning(f"Could not parse fare: {matched_row.get(fare_col)}")
                    excel_fare = 0.0
            
            # Extract mode of transport
            mode_col = None
            for col in df.columns:
                if 'mode' in col or 'transport' in col or col == 'mode_of_transport':
                    mode_col = col
                    break
            
            excel_mode = 'N/A'
            if mode_col and matched_row.get(mode_col):
                excel_mode = str(matched_row[mode_col]).strip().lower()
            
            # Validate status and relation
            validation_error = self._validate_employee_approval(matched_row)
            
            result = {
                'match_found': True,
                'employee_name': employee_name,
                'employee_level': employee_level,
                'fare_limit': fare_limit,
                'match_confidence': confidence,
                'match_type': match_type,
                'all_candidates': [],
                'relation_member': relation_member,
                'relation': relation,
                'status': status,
                # Travel details from Excel for comparison
                'excel_from': excel_from,
                'excel_to': excel_to,
                'excel_fare': excel_fare,
                'excel_mode': excel_mode
            }
            
            # If validation failed, add error and rejection flag
            if validation_error:
                result['validation_error'] = validation_error
                result['auto_reject'] = True
                logger.warning(f"Match validation failed: {validation_error}")
            
            logger.debug(f"Built match result: {result}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to build match result: {str(e)}", exc_info=True)
            raise
    
    def _validate_employee_approval(self, employee_row: Dict[str, Any], log_prefix: str = "") -> Optional[str]:
        """
        Validate employee status and relation before processing.
        
        Args:
            employee_row: Employee data from Excel
            log_prefix: Logging prefix
            
        Returns:
            Error message if validation fails, None if valid
        """
        # Criteria 2: Check status column
        status_col = None
        for col in ['status', 'approval_status', 'employee_status']:
            if col in employee_row:
                status_col = col
                break
        
        if status_col:
            status_value = str(employee_row.get(status_col, '')).strip().lower()
            if status_value not in ['approved', 'approve', 'active']:
                logger.warning(f"{log_prefix}Employee status is '{status_value}' (not approved)")
                return f"Employee status is '{status_value}'. Only approved employees can proceed."
        
        # Criteria 1: Check relation column
        relation_col = None
        for col in ['relation', 'relationship', 'relation_type']:
            if col in employee_row:
                relation_col = col
                break
        
        if relation_col:
            relation_value = str(employee_row.get(relation_col, '')).strip().lower()
            
            # Normalize relation value
            valid_relations_lower = [r.lower() for r in self.VALID_RELATIONS]
            
            if relation_value and relation_value not in valid_relations_lower:
                logger.warning(f"{log_prefix}Invalid relation: '{relation_value}'. Valid: {self.VALID_RELATIONS}")
                return f"Relation '{relation_value}' is not valid. Must be one of: {', '.join(self.VALID_RELATIONS)}"
        
        # All validations passed
        return None
    
    def compare_invoice_with_excel(
        self,
        invoice_data: Dict[str, Any],
        excel_data: Dict[str, Any],
        log_prefix: str = ""
    ) -> Dict[str, Any]:
        """
        Compare extracted invoice data with Excel row data.
        
        Args:
            invoice_data: Data extracted from invoice (from extraction_agent)
            excel_data: Data from Excel row (from find_employee_match)
            log_prefix: Logging prefix
            
        Returns:
            Dict with:
                - matches: bool (all fields match)
                - mismatches: List[str] (list of mismatched fields with details)
                - comparison_details: Dict (field-by-field comparison)
        """
        try:
            mismatches = []
            comparison_details = {}
            
            # Compare origin/from
            invoice_from = str(invoice_data.get('origin', '')).strip().lower()
            excel_from = str(excel_data.get('excel_from', '')).strip().lower()
            
            from_match = invoice_from == excel_from or excel_from == 'n/a'
            comparison_details['from'] = {
                'invoice': invoice_from,
                'excel': excel_from,
                'match': from_match
            }
            
            if not from_match:
                mismatches.append(f"Origin mismatch: Invoice='{invoice_from}' vs Excel='{excel_from}'")
            
            # Compare destination/to
            invoice_to = str(invoice_data.get('destination', '')).strip().lower()
            excel_to = str(excel_data.get('excel_to', '')).strip().lower()
            
            to_match = invoice_to == excel_to or excel_to == 'n/a'
            comparison_details['to'] = {
                'invoice': invoice_to,
                'excel': excel_to,
                'match': to_match
            }
            
            if not to_match:
                mismatches.append(f"Destination mismatch: Invoice='{invoice_to}' vs Excel='{excel_to}'")
            
            # Compare fare
            invoice_fare = float(invoice_data.get('fare', 0.0))
            excel_fare = float(excel_data.get('excel_fare', 0.0))
            
            # Allow small difference (up to 1 rupee for rounding)
            fare_match = abs(invoice_fare - excel_fare) <= 1.0 or excel_fare == 0.0
            comparison_details['fare'] = {
                'invoice': invoice_fare,
                'excel': excel_fare,
                'match': fare_match
            }
            
            if not fare_match:
                mismatches.append(f"Fare mismatch: Invoice=₹{invoice_fare} vs Excel=₹{excel_fare}")
            
            # Compare mode of transport
            invoice_mode = str(invoice_data.get('mode_of_transport', '')).strip().lower()
            excel_mode = str(excel_data.get('excel_mode', '')).strip().lower()
            
            # Skip mode comparison if invoice doesn't have mode (extraction failed)
            if invoice_mode in ['unknown', '', 'n/a']:
                mode_match = True  # Don't reject if mode not extracted
                logger.info(f"{log_prefix}Mode comparison skipped (invoice mode not extracted)")
            else:
                mode_match = invoice_mode == excel_mode or excel_mode == 'n/a'
            
            comparison_details['mode'] = {
                'invoice': invoice_mode,
                'excel': excel_mode,
                'match': mode_match,
                'skipped': invoice_mode in ['unknown', '', 'n/a']
            }
            
            if not mode_match:
                mismatches.append(f"Mode mismatch: Invoice='{invoice_mode}' vs Excel='{excel_mode}'")
            
            # Overall result
            all_match = len(mismatches) == 0
            
            result = {
                'matches': all_match,
                'mismatches': mismatches,
                'comparison_details': comparison_details
            }
            
            if mismatches:
                logger.warning(f"{log_prefix}Data comparison failed: {', '.join(mismatches)}")
            else:
                logger.info(f"{log_prefix}Invoice data matches Excel data")
            
            return result
            
        except Exception as e:
            logger.error(f"{log_prefix}Comparison failed: {str(e)}", exc_info=True)
            return {
                'matches': False,
                'mismatches': [f"Comparison error: {str(e)}"],
                'comparison_details': {}
            }
    
    def _get_default_fare_limit(self, employee_level: str) -> float:
        """
        Get default fare limit based on employee level.
        
        Args:
            employee_level: Employee level code
            
        Returns:
            Default fare limit
        """
        # Default domestic fare limits
        defaults = {
            'a': 15000.0,
            'level a': 15000.0,
            'senior': 15000.0,
            'b': 10000.0,
            'level b': 10000.0,
            'middle': 10000.0,
            'c': 7500.0,
            'level c': 7500.0,
            'junior': 7500.0,
            'd': 5000.0,
            'level d': 5000.0,
            'staff': 5000.0,
        }
        
        level_normalized = employee_level.strip().lower()
        limit = defaults.get(level_normalized, 5000.0)  # Default to lowest tier
        
        logger.info(f"Using default fare limit for level '{employee_level}': {limit}")
        
        return limit
    
    async def extract_proposal_summary(
        self,
        excel_path: Path,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract summary statistics from proposal.
        
        Args:
            excel_path: Path to Excel file
            session_id: Session ID
            
        Returns:
            Summary dict
        """
        try:
            log_prefix = f"[{session_id}] " if session_id else ""
            
            df = excel_utils.load_excel(excel_path)
            df = excel_utils.normalize_employee_data(df)
            
            summary = {
                'total_employees': len(df),
                'unique_names': len(df['name'].unique()) if 'name' in df.columns else 0,
                'levels_present': [],
                'avg_fare_limit': 0.0,
                'columns': list(df.columns)
            }
            
            # Get level distribution
            if 'employee_level' in df.columns:
                levels = df['employee_level'].value_counts().to_dict()
                summary['levels_present'] = levels
            
            # Get average fare limit
            if 'fare_limit' in df.columns:
                avg_limit = df['fare_limit'].mean()
                if not pd.isna(avg_limit):
                    summary['avg_fare_limit'] = float(avg_limit)
            
            logger.info(f"{log_prefix}Proposal summary: {summary['total_employees']} employees")
            
            return summary
            
        except Exception as e:
            logger.error(f"{log_prefix}Proposal summary extraction failed: {str(e)}")
            return {'error': str(e)}


# Singleton instance
excel_agent = ExcelAgent()
