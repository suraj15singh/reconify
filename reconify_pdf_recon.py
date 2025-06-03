#!/usr/bin/env python3

import argparse
import os
import pandas as pd
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Fixed paths
HR_DATA_PATH = "/Users/surajkumarsingh/Documents/sot1/HR Data File Format.csv"
OUTPUT_PATH = "/Users/surajkumarsingh/Documents/reports"

class ReconifyReconciler:
    def __init__(self, tool_path, tool_name="Seller Panel"):
        self.tool_path = tool_path
        self.hr_path = HR_DATA_PATH
        self.output_path = OUTPUT_PATH
        self.tool_name = tool_name
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def validate_input_files(self):
        """Validate input files and required columns."""
        try:
            # Read HR data
            self.hr_df = pd.read_csv(self.hr_path)
            required_hr_columns = ['Official Email Address', 'Employment Status', 'Employee Name']
            if not all(col in self.hr_df.columns for col in required_hr_columns):
                raise ValueError(f"HR data missing required columns: {required_hr_columns}")
            
            # Read tool data
            self.tool_df = pd.read_csv(self.tool_path)
            required_tool_columns = ['user_email', 'role_name', 'user_status', 'created_at']
            if not all(col in self.tool_df.columns for col in required_tool_columns):
                raise ValueError(f"Tool data missing required columns: {required_tool_columns}")
            
            # Convert email addresses to lowercase for case-insensitive matching
            self.hr_df['Official Email Address'] = self.hr_df['Official Email Address'].str.lower()
            self.tool_df['user_email'] = self.tool_df['user_email'].str.lower()
            
            return True
        except Exception as e:
            logger.error(f"Error validating input files: {str(e)}")
            raise

    def find_exceptions(self):
        """Find exceptions in the data."""
        exceptions = []
        
        # Find inactive users with active tool access
        inactive_hr = self.hr_df[self.hr_df['Employment Status'].str.lower() == 'inactive']
        for _, hr_row in inactive_hr.iterrows():
            tool_matches = self.tool_df[self.tool_df['user_email'] == hr_row['Official Email Address']]
            for _, tool_row in tool_matches.iterrows():
                if tool_row['user_status'].lower() not in ['inactive', 'disabled']:
                    # Create a dictionary with all tool data columns
                    exception_data = {
                        'Employee Name': hr_row['Employee Name'],
                        'Email': hr_row['Official Email Address']
                    }
                    # Add all columns from tool data
                    for col in self.tool_df.columns:
                        exception_data[f'Tool {col}'] = tool_row[col]
                    
                    exceptions.append(exception_data)
        
        # Find users in tool but missing in HR
        tool_emails = set(self.tool_df['user_email'])
        hr_emails = set(self.hr_df['Official Email Address'])
        missing_in_hr = tool_emails - hr_emails
        
        for email in missing_in_hr:
            tool_matches = self.tool_df[self.tool_df['user_email'] == email]
            for _, tool_row in tool_matches.iterrows():
                # Create a dictionary with all tool data columns
                exception_data = {
                    'Employee Name': 'N/A',
                    'Email': email
                }
                # Add all columns from tool data
                for col in self.tool_df.columns:
                    exception_data[f'Tool {col}'] = tool_row[col]
                
                exceptions.append(exception_data)
        
        return pd.DataFrame(exceptions)

    def generate_pdf_report(self, exceptions_df):
        """Generate PDF report with exceptions."""
        output_file = os.path.join(
            self.output_path,
            f"reconciliation_report_{self.timestamp}.pdf"
        )
        
        # Calculate available width for table (page width - margins)
        page_width = letter[0]
        available_width = page_width - (36 * 2)  # 36 points margin on each side
        
        doc = SimpleDocTemplate(
            output_file,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=72,
            bottomMargin=72
        )
        
        # Create styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30
        )
        
        # Create red disclaimer style
        disclaimer_style = ParagraphStyle(
            'RedDisclaimer',
            parent=styles['Normal'],
            textColor=colors.red,
            fontSize=12,
            spaceAfter=12
        )
        
        # Create content
        content = []
        
        # Title
        content.append(Paragraph("User Access Reconciliation Report", title_style))
        
        # Report details
        details = [
            f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Source of Truth: {os.path.basename(self.hr_path)}",
            f"App Name: {self.tool_name}"
        ]
        
        for detail in details:
            content.append(Paragraph(detail, styles["Normal"]))
            content.append(Spacer(1, 12))
        
        # Red disclaimer
        content.append(Paragraph("For any discrepancy, contact manish1.taneja@paytm.com", disclaimer_style))
        content.append(Spacer(1, 20))
        
        # Summary
        content.append(Paragraph("Summary", styles["Heading2"]))
        content.append(Paragraph(f"Total discrepancies found: {len(exceptions_df)}", styles["Normal"]))
        content.append(Spacer(1, 20))
        
        # Clean up column names and remove specified columns
        # First remove the role_name column
        if 'Tool role_name' in exceptions_df.columns:
            exceptions_df = exceptions_df.drop(columns=['Tool role_name'])
        
        # Remove user_status columns (both with and without Tool prefix)
        status_columns = ['user_status', 'Tool user_status']
        for col in status_columns:
            if col in exceptions_df.columns:
                exceptions_df = exceptions_df.drop(columns=[col])
        
        # Remove Employee Name column
        if 'Employee Name' in exceptions_df.columns:
            exceptions_df = exceptions_df.drop(columns=['Employee Name'])
        
        # Remove 'Tool' prefix from column names
        exceptions_df.columns = [col.replace('Tool ', '') for col in exceptions_df.columns]
        
        # Keep only one Email column
        if 'Email' in exceptions_df.columns and 'user_email' in exceptions_df.columns:
            exceptions_df = exceptions_df.drop(columns=['user_email'])
        
        # Exceptions table
        if not exceptions_df.empty:
            content.append(Paragraph("Users with Access Discrepancies", styles["Heading2"]))
            content.append(Spacer(1, 12))
            
            # Convert DataFrame to list of lists for table
            table_data = [exceptions_df.columns.tolist()] + exceptions_df.values.tolist()
            
            # Calculate column widths based on content and available width
            num_columns = len(exceptions_df.columns)
            base_width = available_width / num_columns
            
            col_widths = []
            for col in exceptions_df.columns:
                if col == 'Email':
                    col_widths.append(base_width * 1.2)  # 20% wider for email
                else:
                    col_widths.append(base_width)
            
            # Create table with calculated widths
            table = Table(table_data, colWidths=col_widths, repeatRows=1)
            
            # Create table style
            table_style = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),  # Even smaller header font
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 7),  # Even smaller data font
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.beige, colors.white]),  # Alternating row colors
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # Vertical alignment
                ('WORDWRAP', (0, 0), (-1, -1), True),  # Enable word wrapping
                ('LEFTPADDING', (0, 0), (-1, -1), 3),  # Further reduced padding
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('LEADING', (0, 0), (-1, -1), 8),  # Line spacing for wrapped text
            ]
            
            table.setStyle(TableStyle(table_style))
            
            # Convert all cell contents to Paragraph objects for proper wrapping
            for row in range(len(table_data)):
                for col in range(len(table_data[0])):
                    cell_value = str(table_data[row][col])
                    if row == 0:  # Header row
                        table_data[row][col] = Paragraph(cell_value, ParagraphStyle(
                            'TableHeader',
                            fontName='Helvetica-Bold',
                            fontSize=8,
                            alignment=1,  # Center alignment
                            leading=8
                        ))
                    else:  # Data rows
                        table_data[row][col] = Paragraph(cell_value, ParagraphStyle(
                            'TableData',
                            fontName='Helvetica',
                            fontSize=7,
                            alignment=1,  # Center alignment
                            leading=8
                        ))
            
            # Recreate table with wrapped content
            table = Table(table_data, colWidths=col_widths, repeatRows=1)
            table.setStyle(TableStyle(table_style))
            
            content.append(table)
            content.append(Spacer(1, 12))  # Add space after table
        
        # Build PDF
        doc.build(content)
        logger.info(f"PDF report generated: {output_file}")
        return output_file

def validate_paths(tool_path):
    """Validate all input and output paths."""
    # Check if input files exist
    if not os.path.isfile(tool_path):
        raise FileNotFoundError(f"Tool data file not found: {tool_path}")
    if not os.path.isfile(HR_DATA_PATH):
        raise FileNotFoundError(f"HR data file not found at fixed path: {HR_DATA_PATH}")
    
    # Create output directory if it doesn't exist
    try:
        os.makedirs(OUTPUT_PATH, exist_ok=True)
    except OSError as e:
        raise OSError(f"Cannot create output directory '{OUTPUT_PATH}'. Please check permissions and try again. Error: {str(e)}")
    
    # Check if output directory is writable
    if not os.access(OUTPUT_PATH, os.W_OK):
        raise OSError(f"Output directory '{OUTPUT_PATH}' is not writable. Please check permissions and try again.")

def get_tool_data_path():
    """Prompt user for tool data file path."""
    default_path = "/Users/surajkumarsingh/Documents/panel data/1. Seller Panel Users List with Assigned Roles - 1. Seller Panel Users List with Assigned Roles.csv"
    
    print(f"Default tool data path: {default_path}")
    print("Press Enter to use default path or enter a different path:")
    
    user_input = input().strip()
    
    # Use default path if user just presses Enter
    tool_path = default_path if not user_input else user_input
    
    # Remove any quotes from the path
    tool_path = tool_path.strip("'\"")
    
    if os.path.isfile(tool_path):
        return os.path.abspath(tool_path)
    else:
        print(f"Error: File not found at {tool_path}")
        print("Please check if the file exists and try again.")
        return get_tool_data_path()  # Recursively ask again

def main():
    parser = argparse.ArgumentParser(description='HR Data Reconciliation Tool')
    parser.add_argument('--tool_name', default='Seller Panel', help='Name of the tool')
    parser.add_argument('--output_format', choices=['pdf', 'csv'], default='pdf', help='Output format')
    
    args = parser.parse_args()
    
    try:
        # Get tool data path from user
        tool_path = get_tool_data_path()
        
        # Validate paths
        validate_paths(tool_path)
        
        # Initialize reconciler
        reconciler = ReconifyReconciler(
            tool_path,
            args.tool_name
        )
        
        # Validate input files
        reconciler.validate_input_files()
        
        # Find exceptions
        exceptions_df = reconciler.find_exceptions()
        
        # Generate report
        if args.output_format == 'pdf':
            output_file = reconciler.generate_pdf_report(exceptions_df)
        else:
            output_file = os.path.join(
                OUTPUT_PATH,
                f"reconciliation_report_{reconciler.timestamp}.csv"
            )
            exceptions_df.to_csv(output_file, index=False)
        
        logger.info(f"Report generated successfully: {output_file}")
        logger.info(f"Found {len(exceptions_df)} users with active tool access but inactive in HR")
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {str(e)}")
        raise
    except OSError as e:
        logger.error(f"File system error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    main() 