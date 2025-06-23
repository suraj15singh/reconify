#!/usr/bin/env python3

import argparse
import os
import pandas as pd
from datetime import datetime
import logging
from config_handler import ConfigHandler
from report_formats import ReportFormats

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
HR_DATA_PATH = '/Users/surajkumarsingh/Documents/sot1/HR Data File Format.csv'
REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
SUPPORT_EMAIL = "manish1.taneja@paytm.com"

class ReconifyReconciler:
    def __init__(self, app_name: str, hr_data_path: str = None):
        """Initialize the reconciler with configuration."""
        self.config_handler = ConfigHandler()
        self.app_name = app_name
        self.app_config = self.config_handler.get_app_config(app_name)
        self.report_formats = ReportFormats()
        self.recon_id = f"RECON_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create output directory if it doesn't exist
        self.output_dir = REPORTS_DIR
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize data paths
        self.hr_path = hr_data_path
        self.panel_path = None
        
        # Initialize DataFrames
        self.hr_df = None
        self.panel_df = None
        self.exceptions_df = None
        
    def set_panel_path(self, panel_path: str):
        """Set the panel data path.
        
        Args:
            panel_path (str): Path to the panel data file
        """
        self.panel_path = panel_path
        
    def validate_input_files(self) -> bool:
        """Validate input files against configuration requirements.
        
        Returns:
            bool: True if validation passes, False otherwise
        """
        try:
            # Load panel data
            if self.panel_path.endswith('.xlsx'):
                self.panel_df = pd.read_excel(self.panel_path)
            else:
                self.panel_df = pd.read_csv(self.panel_path)
            
            # Get expected columns from config
            panel_email_col = self.config_handler.get_panel_email_column(self.app_name)
            if panel_email_col not in self.panel_df.columns:
                logger.error(f"Panel data missing required column: {panel_email_col}")
                return False
            
            # Initialize exceptions DataFrame
            self.find_exceptions()
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating input files: {str(e)}")
            return False
    
    def _normalize_dataframes(self):
        """Normalize field names in both DataFrames based on configuration."""
        # Get mappings for both sources
        hr_mappings = self.config_handler.get_source_mappings(self.app_name, 'HR_Data')
        panel_mappings = self.config_handler.get_source_mappings(self.app_name, 'SellerPanel_Data')
        
        # Rename columns in HR DataFrame
        self.hr_df = self.hr_df.rename(columns=hr_mappings)
        
        # Rename columns in panel DataFrame
        self.panel_df = self.panel_df.rename(columns=panel_mappings)
    
    def find_exceptions(self):
        """Find exceptions between HR and panel data."""
        if self.panel_df is None:
            raise ValueError("Panel DataFrame not initialized. Call validate_input_files first.")
        
        # Get column names from mapping
        panel_email_col = self.config_handler.get_panel_email_column(self.app_name)
        
        # Create exceptions DataFrame
        exceptions = []
        for _, row in self.panel_df.iterrows():
            exceptions.append({
                'email': row[panel_email_col],
                'role': row.get('role_name', 'N/A'),
                'action': 'revoke',
                'pre_status': 'active',
                'post_status': 'inactive'
            })
        
        self.exceptions_df = pd.DataFrame(exceptions)
    
    def generate_csv_report(self, source_file: str) -> str:
        """Generate CSV report with panel level and user level data in the same file."""
        if self.exceptions_df is None:
            raise ValueError("No exceptions found. Call find_exceptions first.")
        
        # Create output directory if it doesn't exist
        os.makedirs(REPORTS_DIR, exist_ok=True)
        
        # Generate timestamp for filename
        timestamp = datetime.now().strftime("%d%m%Y_%H%M%S")
        output_path = os.path.join(REPORTS_DIR, f"reconciliation_report_{timestamp}.csv")
        
        # Get app display name from config or use app_name
        app_display_name = self.app_config.get('name', self.app_name)
        
        # Create panel level data with proper parent-child column structure
        panel_data = {
            'Panel Name': [app_display_name],
            'Total Users': [len(self.panel_df)],
            'Overall Summary - HR Reconciliation': {
                'Active': [len(self.panel_df) - len(self.exceptions_df)],
                'Inactive': [0],
                'Others (Not Found)': [len(self.exceptions_df)]
            },
            'Others (Not Found) - Summary': {
                'Service IDs': [0],
                'Third Party Users (Dritm)': [0],
                'Group Entity (e.g. Zomato / PPSL)': [0],
                'Vendor / Auditor / Consultant': [0]
            },
            'Inactive - Reason for action': {
                'Entity Movement': [0],
                'Incorrect Email ID': [0],
                'Dual Accounts': [0],
                'Others': [len(self.exceptions_df)]
            }
        }
        
        # Write both tables to the same CSV file
        with open(output_path, 'w') as f:
            # Write panel level report
            f.write("PANEL LEVEL REPORT - FOR IT / AUDIT TEAM\n")
            
            # Write the header rows with proper structure for merging
            # First row: Parent headers (written only once)
            parent_headers = ['Panel Name', 'Total Users', 'Overall Summary - HR Reconciliation', '', '',
                             'Others (Not Found) - Summary', '', '', '',
                             'Inactive - Reason for action', '', '', '']
            f.write(','.join(parent_headers) + '\n')
            
            # Second row: Sub-headers
            sub_headers = ['', '', 'Active', 'Inactive', 'Others (Not Found)',
                          'Service IDs', 'Third Party Users (Dritm)', 
                          'Group Entity (e.g. Zomato / PPSL)', 'Vendor / Auditor / Consultant',
                          'Entity Movement', 'Incorrect Email ID', 'Dual Accounts', 'Others']
            f.write(','.join(sub_headers) + '\n')
            
            # Write the data rows
            data_row = [
                panel_data['Panel Name'][0],
                panel_data['Total Users'][0],
                panel_data['Overall Summary - HR Reconciliation']['Active'][0],
                panel_data['Overall Summary - HR Reconciliation']['Inactive'][0],
                panel_data['Overall Summary - HR Reconciliation']['Others (Not Found)'][0],
                panel_data['Others (Not Found) - Summary']['Service IDs'][0],
                panel_data['Others (Not Found) - Summary']['Third Party Users (Dritm)'][0],
                panel_data['Others (Not Found) - Summary']['Group Entity (e.g. Zomato / PPSL)'][0],
                panel_data['Others (Not Found) - Summary']['Vendor / Auditor / Consultant'][0],
                panel_data['Inactive - Reason for action']['Entity Movement'][0],
                panel_data['Inactive - Reason for action']['Incorrect Email ID'][0],
                panel_data['Inactive - Reason for action']['Dual Accounts'][0],
                panel_data['Inactive - Reason for action']['Others'][0]
            ]
            f.write(','.join(map(str, data_row)) + '\n')
            
            f.write("\n\n")  # Add spacing between tables
            
            # Write user level report
            f.write("USER LEVEL REPORT - FOR IT / AUDIT TEAM\n")
            user_level_data = {
                'User Email ID': self.exceptions_df['email'],
                'Panel Name': [app_display_name] * len(self.exceptions_df),
                'Pre Recon Status': self.exceptions_df['pre_status'],
                'Date of Reconciliation': [datetime.now().strftime("%d/%m/%Y")] * len(self.exceptions_df),
                'Post Recon Status': self.exceptions_df['post_status']
            }
            user_level_df = pd.DataFrame(user_level_data)
            user_level_df.to_csv(f, index=False)
        
        return output_path

def validate_paths(tool_path):
    """Validate all input and output paths."""
    # Check if input files exist
    if not os.path.isfile(tool_path):
        raise FileNotFoundError(f"Tool data file not found: {tool_path}")
    if not os.path.isfile(HR_DATA_PATH):
        raise FileNotFoundError(f"HR data file not found at fixed path: {HR_DATA_PATH}")
    
    # Create output directory if it doesn't exist
    try:
        os.makedirs(REPORTS_DIR, exist_ok=True)
    except OSError as e:
        raise OSError(f"Cannot create output directory '{REPORTS_DIR}'. Please check permissions and try again. Error: {str(e)}")
    
    # Check if output directory is writable
    if not os.access(REPORTS_DIR, os.W_OK):
        raise OSError(f"Output directory '{REPORTS_DIR}' is not writable. Please check permissions and try again.")

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
        return get_tool_data_path()

def main():
    parser = argparse.ArgumentParser(description='HR Data Reconciliation Tool')
    parser.add_argument('--tool_name', default='SellerPanel', help='Name of the tool')
    
    args = parser.parse_args()
    
    try:
        # Get tool data path from user
        tool_path = get_tool_data_path()
        
        # Initialize reconciler
        reconciler = ReconifyReconciler(args.tool_name, tool_path)
        reconciler.set_panel_path(tool_path)
        
        # Validate input files
        if not reconciler.validate_input_files():
            logger.error("Input file validation failed")
            return
        
        # Find exceptions
        reconciler.find_exceptions()
        
        # Generate CSV report
        output_file = reconciler.generate_csv_report(tool_path)
        
        logger.info(f"Report generated successfully: {output_file}")
        logger.info(f"Found {len(reconciler.exceptions_df)} users to revoke access")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    main() 