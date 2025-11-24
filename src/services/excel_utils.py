"""
Excel parsing utilities for proposal data extraction.
"""

import pandas as pd
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from src.config.settings import settings

logger = logging.getLogger(__name__)


class ExcelUtils:
    """Utilities for Excel file processing."""
    
    @staticmethod
    def load_excel(file_path: Path) -> pd.DataFrame:
        """
        Load Excel file into DataFrame.
        
        Args:
            file_path: Path to Excel file
            
        Returns:
            DataFrame with normalized column names
            
        Raises:
            Exception: If file cannot be read
        """
        try:
            # Determine file type
            file_ext = file_path.suffix.lower()
            
            if file_ext == '.csv':
                df = pd.read_csv(file_path)
            elif file_ext in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path)
            else:
                raise Exception(f"Unsupported file format: {file_ext}")
            
            # Normalize column names: lowercase, strip whitespace
            df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
            
            logger.info(f"Loaded Excel: {file_path.name} ({len(df)} rows, {len(df.columns)} columns)")
            logger.debug(f"Columns: {list(df.columns)}")
            
            return df
            
        except pd.errors.EmptyDataError:
            logger.error("Excel file is empty")
            raise Exception("Excel file is empty")
            
        except Exception as e:
            logger.error(f"Failed to load Excel: {str(e)}", exc_info=True)
            raise Exception(f"Failed to parse Excel file: {str(e)}")
    
    @staticmethod
    def validate_columns(df: pd.DataFrame, required_columns: List[str]) -> bool:
        """
        Check if DataFrame has required columns.
        
        Args:
            df: DataFrame to validate
            required_columns: List of required column names
            
        Returns:
            True if all columns present
            
        Raises:
            Exception: If columns are missing
        """
        missing_columns = []
        
        for col in required_columns:
            # Check for exact match or similar variations
            found = False
            for df_col in df.columns:
                if col.lower() in df_col or df_col in col.lower():
                    found = True
                    break
            
            if not found:
                missing_columns.append(col)
        
        if missing_columns:
            available = list(df.columns)
            logger.error(f"Missing columns: {missing_columns}. Available: {available}")
            raise Exception(f"Excel missing required columns: {missing_columns}")
        
        logger.debug("All required columns found")
        return True
    
    @staticmethod
    def normalize_employee_data(df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize employee data for consistent processing.
        
        Args:
            df: Raw DataFrame
            
        Returns:
            Normalized DataFrame
        """
        try:
            df_normalized = df.copy()
            
            # Strip whitespace from string columns
            for col in df_normalized.select_dtypes(include=['object']).columns:
                df_normalized[col] = df_normalized[col].astype(str).str.strip()
            
            # Replace NaN with None for better handling
            df_normalized = df_normalized.where(pd.notnull(df_normalized), None)
            
            # Convert employee level to lowercase for consistency
            if 'employee_level' in df_normalized.columns:
                df_normalized['employee_level'] = df_normalized['employee_level'].astype(str).str.lower()
            
            # Ensure fare_limit is numeric
            if 'fare_limit' in df_normalized.columns:
                df_normalized['fare_limit'] = pd.to_numeric(
                    df_normalized['fare_limit'], 
                    errors='coerce'
                )
            
            logger.debug("Employee data normalized")
            
            return df_normalized
            
        except Exception as e:
            logger.error(f"Failed to normalize data: {str(e)}", exc_info=True)
            raise Exception(f"Data normalization failed: {str(e)}")
    
    @staticmethod
    def get_employee_by_name(df: pd.DataFrame, name: str) -> Optional[Dict[str, Any]]:
        """
        Find employee by exact name match.
        
        Args:
            df: Employee DataFrame
            name: Employee name to search
            
        Returns:
            Employee data dict or None
        """
        try:
            # Normalize search name
            search_name = name.strip().lower()
            
            # Search in name column
            name_col = None
            for col in df.columns:
                if 'name' in col:
                    name_col = col
                    break
            
            if not name_col:
                logger.warning("No name column found in Excel")
                return None
            
            # Find exact match
            mask = df[name_col].astype(str).str.strip().str.lower() == search_name
            matches = df[mask]
            
            if len(matches) == 0:
                logger.debug(f"No exact match found for: {name}")
                return None
            
            if len(matches) > 1:
                logger.warning(f"Multiple exact matches found for: {name}")
            
            # Return first match as dict
            employee_data = matches.iloc[0].to_dict()
            logger.debug(f"Found employee: {employee_data}")
            
            return employee_data
            
        except Exception as e:
            logger.error(f"Employee lookup error: {str(e)}", exc_info=True)
            return None
    
    @staticmethod
    def get_all_names(df: pd.DataFrame) -> List[str]:
        """
        Extract all employee names from DataFrame.
        
        Args:
            df: Employee DataFrame
            
        Returns:
            List of names
        """
        try:
            name_col = None
            for col in df.columns:
                if 'name' in col:
                    name_col = col
                    break
            
            if not name_col:
                logger.warning("No name column found")
                return []
            
            names = df[name_col].astype(str).str.strip().tolist()
            names = [n for n in names if n and n.lower() != 'nan']
            
            logger.debug(f"Extracted {len(names)} employee names")
            
            return names
            
        except Exception as e:
            logger.error(f"Name extraction error: {str(e)}", exc_info=True)
            return []


# Singleton instance
excel_utils = ExcelUtils()
