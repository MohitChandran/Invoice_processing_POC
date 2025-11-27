#!/usr/bin/env python3
"""
Test script for new validation criteria
"""

import pandas as pd
from pathlib import Path

# Create sample Excel file with new columns
def create_test_excel():
    data = {
        'name': ['John Doe', 'Alice Smith', 'Mike Johnson', 'Sarah Lee', 'Bob Wilson'],
        'employee_level': ['Senior', 'Junior', 'Senior', 'Middle', 'Junior'],
        'fare_limit': [10000, 5000, 10000, 7500, 5000],
        'relation_member': ['Jane Doe', 'Bob Smith', 'Tom Friend', 'David Lee', 'Mary Wilson'],
        'relation': ['wife', 'son', 'friend', 'husband', 'mother'],
        'status': ['approved', 'approved', 'approved', 'rejected', 'approved']
    }
    
    df = pd.DataFrame(data)
    
    output_path = Path('test_validation_criteria.xlsx')
    df.to_excel(output_path, index=False)
    
    print("✅ Test Excel file created: test_validation_criteria.xlsx")
    print("\nSample Data:")
    print(df.to_string(index=False))
    print("\n" + "="*80)
    print("Expected Results:")
    print("="*80)
    print("✅ John Doe (wife, approved) → SHOULD PASS")
    print("✅ Alice Smith (son, approved) → SHOULD PASS")
    print("❌ Mike Johnson (friend, approved) → SHOULD REJECT (invalid relation)")
    print("❌ Sarah Lee (husband, rejected) → SHOULD REJECT (status not approved)")
    print("✅ Bob Wilson (mother, approved) → SHOULD PASS")
    print("="*80)

if __name__ == '__main__':
    create_test_excel()
