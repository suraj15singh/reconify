# Reconify - HR Data Reconciliation Tool

A CLI tool for reconciling HR data with tool user access and generating structured PDF reports.

## Features

- Compares HR data with tool access data
- Identifies inactive users with active tool access
- Generates detailed PDF reports for audit/compliance
- Supports CSV input formats
- Case-insensitive email matching
- Detailed exception reporting

## Installation

1. Clone this repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

```bash
python reconify_pdf_recon.py \
  --tool_path /path/to/tool.csv \
  --hr_path /path/to/hr.csv \
  --output_path /desired/folder \
  --tool_name "Reconify Tool"
```

### Arguments

- `--tool_path`: Path to the tool access CSV file
- `--hr_path`: Path to the HR data CSV file
- `--output_path`: Directory where the report will be saved
- `--tool_name`: Name of the tool (defaults to "Reconify Tool")
- `--output_format`: Output format (pdf or csv, defaults to pdf)

## Input File Requirements

### HR Data CSV
Required columns:
- Official Email Address
- Employment Status
- Employee Name (optional)
- L1 Manager Code (optional)
- HOD Code (optional)

### Tool Data CSV
Required columns:
- user_email
- role_name
- user_status
- created_at

## Output

Generates a PDF report containing:
- Reconciliation summary
- Detailed exception list
- User status comparison
- Audit trail information 