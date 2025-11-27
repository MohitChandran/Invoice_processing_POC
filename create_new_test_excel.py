"""
Create test Excel file with NEW structure for multi-invoice validation.

New Excel Structure:
- Each row = one person (employee OR dependent)
- Columns: employee_level, name, from, to, relation, fare, mode_of_transport, status
- relation='self' → primary employee (has employee_level)
- relation≠'self' → dependent (employee_level = NULL)
"""

import pandas as pd
from pathlib import Path

# Test data with new structure
test_data = [
    # Employee 1 (Mohit - self) + dependents
    {
        'employee_level': 'L2',
        'name': 'Mohit',
        'from': 'Salem',
        'to': 'Chennai',
        'relation': 'self',
        'fare': 500,
        'mode_of_transport': 'bus',
        'status': 'approved'
    },
    {
        'employee_level': None,  # NULL for dependent
        'name': 'Uma',
        'from': 'Salem',
        'to': 'Chennai',
        'relation': 'mother',
        'fare': 500,
        'mode_of_transport': 'bus',
        'status': 'approved'
    },
    {
        'employee_level': None,
        'name': 'Sanjana',
        'from': 'Salem',
        'to': 'Bangalore',
        'relation': 'wife',
        'fare': 800,
        'mode_of_transport': 'train',
        'status': 'approved'
    },
    
    # Employee 2 (John - self) + dependents
    {
        'employee_level': 'L1',
        'name': 'John Doe',
        'from': 'Mumbai',
        'to': 'Delhi',
        'relation': 'self',
        'fare': 6500,
        'mode_of_transport': 'flight',
        'status': 'approved'
    },
    {
        'employee_level': None,
        'name': 'Mary Doe',
        'from': 'Mumbai',
        'to': 'Delhi',
        'relation': 'wife',
        'fare': 6500,
        'mode_of_transport': 'flight',
        'status': 'approved'
    },
    {
        'employee_level': None,
        'name': 'Tim Doe',
        'from': 'Mumbai',
        'to': 'Pune',
        'relation': 'son',
        'fare': 2000,
        'mode_of_transport': 'train',
        'status': 'approved'
    },
    
    # Employee 3 (Sarah - self) - REJECTED status for testing
    {
        'employee_level': 'L3',
        'name': 'Sarah Lee',
        'from': 'Bangalore',
        'to': 'Hyderabad',
        'relation': 'self',
        'fare': 3500,
        'mode_of_transport': 'train',
        'status': 'rejected'  # Should be rejected
    },
    
    # Employee 4 (Bob - self) + invalid dependent for testing
    {
        'employee_level': 'L2',
        'name': 'Bob Wilson',
        'from': 'Chennai',
        'to': 'Kochi',
        'relation': 'self',
        'fare': 4000,
        'mode_of_transport': 'bus',
        'status': 'approved'
    },
    {
        'employee_level': None,
        'name': 'Alice Smith',
        'from': 'Chennai',
        'to': 'Kochi',
        'relation': 'friend',  # Invalid relation - should be rejected
        'fare': 4000,
        'mode_of_transport': 'bus',
        'status': 'approved'
    },
    
    # Employee 5 (Emma - self) - for fare mismatch testing
    {
        'employee_level': 'L1',
        'name': 'Emma Brown',
        'from': 'Delhi',
        'to': 'Agra',
        'relation': 'self',
        'fare': 1500,
        'mode_of_transport': 'car',
        'status': 'approved'
    },
]

# Create DataFrame
df = pd.DataFrame(test_data)

# Save to Excel
output_path = Path('data/uploads/proposals/new_structure_test_proposal.xlsx')
output_path.parent.mkdir(parents=True, exist_ok=True)

# Try openpyxl first, fallback to xlsxwriter
try:
    df.to_excel(output_path, index=False, sheet_name='Travelers', engine='openpyxl')
except ImportError:
    try:
        df.to_excel(output_path, index=False, sheet_name='Travelers', engine='xlsxwriter')
    except ImportError:
        # If no Excel engine available, save as CSV
        output_path = output_path.with_suffix('.csv')
        df.to_csv(output_path, index=False)
        print(f"⚠️  No Excel library available, saved as CSV instead")

print(f"✅ Test Excel created: {output_path}")
print(f"\n📊 Excel Structure:")
print(f"   Total rows: {len(df)}")
print(f"   Columns: {', '.join(df.columns)}")
print(f"\n📋 Sample data:")
print(df.to_string(index=False))

print(f"\n🧪 Test Scenarios:")
print("1. ✅ Mohit (self, L2, bus, approved) - Should pass policy validation")
print("2. ✅ Uma (mother, bus, approved) - Should auto-approve (dependent, data match)")
print("3. ✅ Sanjana (wife, train, approved) - Should auto-approve (dependent, data match)")
print("4. ✅ John Doe (self, L1, flight, approved) - Should pass policy validation")
print("5. ✅ Mary Doe (wife, flight, approved) - Should auto-approve (dependent)")
print("6. ✅ Tim Doe (son, train, approved) - Should auto-approve (dependent)")
print("7. ❌ Sarah Lee (self, L3, rejected status) - Should reject (status not approved)")
print("8. ✅ Bob Wilson (self, L2, bus, approved) - Should pass policy validation")
print("9. ❌ Alice Smith (friend, invalid relation) - Should reject (invalid relation)")
print("10. ✅ Emma Brown (self, L1, car, approved) - For fare mismatch testing")

print(f"\n💡 Usage:")
print("1. Upload this Excel as proposal")
print("2. Create matching invoices for each person")
print("3. Test batch validation with multiple invoices")
print("4. Verify:")
print("   - relation='self' → Policy validation applied")
print("   - relation≠'self' → Only data comparison, auto-approve if match")
print("   - status='rejected' → Pre-validation rejection")
print("   - relation='friend' → Invalid relation rejection")
print("   - Data mismatch → Comparison rejection")
