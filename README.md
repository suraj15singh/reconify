# User Access Management System

A comprehensive web-based system for managing and reconciling user access across different platforms.

## Features

- File upload and validation for HR and Panel data
- Primary key selection (Email/Employee ID)
- Reconciliation process management with unique Process IDs
- Comprehensive audit trail
- Report generation and filtering
- Downloadable reports in PDF and CSV formats

## Setup Instructions

1. Clone the repository:
```bash
git clone https://github.com/yourusername/reconify.git
cd reconify
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the Streamlit app:
```bash
streamlit run streamlit_app.py
```

## Usage

1. **Upload Files**
   - Upload HR data CSV file
   - Upload Panel data CSV file
   - Select primary key for mapping (Email or Employee ID)

2. **Process Data**
   - Click "Start Reconciliation" to begin the process
   - A unique Process ID will be generated
   - Validation results will be displayed
   - Reconciliation report will be generated

3. **View Reports**
   - Access reports in the "Reports" tab
   - Filter reports by Process ID, date range, reconciliation level, and employment status
   - Download reports in PDF format

4. **Audit Trail**
   - View complete audit trail in the "Audit Trail" tab
   - Download audit trail as CSV

## File Format Requirements

### HR Data CSV
Required columns:
- Official Email Address
- Employment Status
- Employee Name

### Panel Data CSV
Required columns:
- user_email
- role_name
- user_status
- created_at

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 