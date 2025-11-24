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
                return self._build_match_result(
                    df=df,
                    matched_row=exact_match,
                    match_type='exact',
                    confidence=1.0
                )
            
            # Try fuzzy matching
            logger.info(f"{log_prefix}Exact match not found, trying fuzzy match...")
            fuzzy_result = await self._fuzzy_match_employee(df, passenger_name)
            
            if fuzzy_result['match_found']:
                logger.info(f"{log_prefix}Found fuzzy match: {fuzzy_result['employee_name']} "
                          f"(confidence: {fuzzy_result['match_confidence']:.2f})")
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
            
            # Perform fuzzy matching
            matches = process.extract(target_name, all_names, scorer=fuzz.token_sort_ratio, limit=5)
            
            logger.debug(f"Fuzzy matches: {matches}")
            
            # Check best match
            best_match_name, best_score = matches[0]
            
            if best_score >= self.fuzzy_threshold:
                # Good match found
                matched_row = excel_utils.get_employee_by_name(df, best_match_name)
                
                if matched_row:
                    # Check for ambiguous matches
                    ambiguous = False
                    candidates = []
                    
                    for match_name, score in matches:
                        if score >= self.fuzzy_threshold:
                            candidates.append({
                                'name': match_name,
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
            
            # No good match
            return {
                'match_found': False,
                'employee_name': target_name,
                'employee_level': 'unknown',
                'fare_limit': 0.0,
                'match_confidence': best_score / 100.0,
                'match_type': 'none',
                'all_candidates': [{'name': m[0], 'score': m[1] / 100.0} for m in matches[:3]]
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
            
            result = {
                'match_found': True,
                'employee_name': employee_name,
                'employee_level': employee_level,
                'fare_limit': fare_limit,
                'match_confidence': confidence,
                'match_type': match_type,
                'all_candidates': []
            }
            
            logger.debug(f"Built match result: {result}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to build match result: {str(e)}", exc_info=True)
            raise
    
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
