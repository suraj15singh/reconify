import streamlit as st
import pandas as pd
import os
from datetime import datetime
import uuid
import logging
from reconify_pdf_recon import ReconifyReconciler
from config_handler import ConfigHandler
import json
import random
from db_handler import DatabaseHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize session state
if 'process_id' not in st.session_state:
    st.session_state.process_id = None
if 'audit_trail' not in st.session_state:
    st.session_state.audit_trail = []

# Initialize database connection
db = DatabaseHandler()

def generate_process_id():
    """Generate a process ID in the format REC-DDMMYYYY-HHMMSS."""
    timestamp = datetime.now().strftime('%d%m%Y-%H%M%S')  # DDMMYYYY-HHMMSS format
    return f"REC-{timestamp}"  # Example: REC-15032024-143022

def save_uploaded_file(uploaded_file):
    """Save uploaded file to temporary location."""
    if uploaded_file is not None:
        # Create temp directory if it doesn't exist
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_uploads")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Get file extension
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        # Save file
        file_path = os.path.join(temp_dir, f"{file_extension}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_extension}")
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    return None

def get_app_list():
    """Get list of available applications from config."""
    config_handler = ConfigHandler()
    return config_handler.get_all_apps()

def to_pascal_case(text):
    """Convert text to PascalCase."""
    if not text:
        return text
    return ''.join(word.capitalize() for word in str(text).split('_'))

def generate_reconciliation_id(app_name):
    """Generate a reconciliation ID in the format RCN_appname_number."""
    timestamp = datetime.now().strftime('%d%m%Y%H%M%S')  # DDMMYYYYHHMMSS format
    return f"RCN_{app_name}_{timestamp}"  # Example: RCN_SellerPanel_15032024143022

def main():
    st.set_page_config(page_title="Reconify", layout="wide")
    st.title("Reconify - Reconciliation Tool")

    # Initialize session state
    if 'reconciliation_results' not in st.session_state:
        st.session_state.reconciliation_results = None
    if 'current_tab' not in st.session_state:
        st.session_state.current_tab = "Primary Data Upload"
    if 'primary_upload_complete' not in st.session_state:
        st.session_state.primary_upload_complete = False
    if 'selected_app' not in st.session_state:
        st.session_state.selected_app = None
    if 'process_id' not in st.session_state:
        st.session_state.process_id = generate_process_id()
    if 'upload_history' not in st.session_state:
        st.session_state.upload_history = []

    # Create tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "Primary Data Upload", 
        "Secondary Data Upload", 
        "Data Mapping", 
        "Reconciliation Results", 
        "Reports",
        "Audit Trails",
        "File Upload History"
    ])

    with tab1:
        st.header("Primary Data Upload")
        
        # Application Data Upload
        st.subheader("Application Data Upload")
        
        # Get list of available applications
        config_handler = ConfigHandler()
        available_apps = config_handler.get_all_apps_with_names()
        
        # App selection
        selected_app = st.selectbox(
            "Select Application",
            options=list(available_apps.keys()),
            format_func=lambda x: available_apps[x]
        )
        
        if selected_app:
            st.session_state.selected_app = selected_app
            st.info(f"Selected Application: {available_apps[selected_app]}")
            st.write(f"Description: {config_handler.get_app_description(selected_app)}")
            
            # Show expected field mapping
            if 'SOT' in config_handler.get_app_config(selected_app):
                st.write("Expected Field Mapping:")
                for source, target in config_handler.get_app_config(selected_app)['SOT']['HR_Data'].items():
                    st.write(f"HR Data: {source} → Application Data: {target}")
        
        app_file = st.file_uploader("Upload Application Data (CSV/Excel)", type=['csv', 'xlsx'])
        if app_file:
            try:
                app_df = pd.read_csv(app_file) if app_file.name.endswith('.csv') else pd.read_excel(app_file)
                
                # Verify required fields exist
                if selected_app and 'SOT' in config_handler.get_app_config(selected_app):
                    required_field = config_handler.get_app_config(selected_app)['SOT']['HR_Data']['Official Email Address']
                    if required_field not in app_df.columns:
                        st.error(f"Required field '{required_field}' not found in the uploaded file.")
                        st.stop()
                
                # Reset index to start from 1 and rename it to S.No.
                app_df.index = range(1, len(app_df) + 1)
                app_df.index.name = 'S.No.'
                # Remove commas from L1 manager code if it exists
                if 'L1 Manager Code' in app_df.columns:
                    app_df['L1 Manager Code'] = app_df['L1 Manager Code'].astype(str).str.replace(',', '')
                st.success(f"Successfully loaded Application data with {len(app_df)} records")
                st.session_state.app_data = app_df
                # Display first few rows of Application data
                st.write("Preview of Application Data:")
                st.dataframe(app_df)
                
                # Add to upload history
                st.session_state.upload_history.append({
                    'timestamp': datetime.now().strftime('%d-%m-%Y %H:%M:%S'),
                    'file_type': 'Application Data',
                    'file_name': app_file.name,
                    'records': len(app_df),
                    'application': available_apps[selected_app]
                })
            except Exception as e:
                st.error(f"Error loading Application data: {str(e)}")

        # HR Data Loading from fixed path
        st.subheader("HR Data")
        hr_file_path = '/Users/surajkumarsingh/Documents/sot1/HR Data File Format.csv'
        try:
            hr_df = pd.read_csv(hr_file_path)
            # Reset index to start from 1 and rename it to S.No.
            hr_df.index = range(1, len(hr_df) + 1)
            hr_df.index.name = 'S.No.'
            # Remove commas from L1 manager code if it exists
            if 'L1 Manager Code' in hr_df.columns:
                hr_df['L1 Manager Code'] = hr_df['L1 Manager Code'].astype(str).str.replace(',', '')
            st.success(f"Last HR Data fetched: Employee Count: {len(hr_df)}, Date: {datetime.now().strftime('%d-%m-%Y')}")
            st.session_state.hr_data = hr_df
            
            # Add to upload history
            st.session_state.upload_history.append({
                'timestamp': datetime.now().strftime('%d-%m-%Y %H:%M:%S'),
                'file_type': 'HR Data',
                'file_name': 'HR Data File Format.csv',
                'records': len(hr_df),
                'application': 'N/A'
            })
        except Exception as e:
            st.error(f"Error loading HR data: {str(e)}")

        # Reconcile button
        if 'hr_data' in st.session_state and 'app_data' in st.session_state and st.session_state.selected_app:
            if st.button("Start Reconciliation", type="primary"):
                try:
                    # Initialize reconciler with selected app
                    reconciler = ReconifyReconciler(app_name=st.session_state.selected_app)
                    
                    # Set the panel data
                    reconciler.panel_df = st.session_state.app_data
                    reconciler.hr_df = st.session_state.hr_data
                    
                    # Get the email field mapping from config
                    app_config = config_handler.get_app_config(st.session_state.selected_app)
                    hr_email_field = list(app_config['SOT']['HR_Data'].keys())[0]  # e.g., "Official Email Address"
                    panel_email_field = app_config['SOT']['HR_Data'][hr_email_field]  # e.g., "user_email"
                    
                    # Create exceptions DataFrame
                    exceptions = []
                    for _, row in reconciler.panel_df.iterrows():
                        if panel_email_field not in row:
                            st.error(f"Required field '{panel_email_field}' not found in the uploaded file.")
                            st.stop()
                            
                        email = row[panel_email_field]
                        # Check if email exists in HR data
                        if email not in reconciler.hr_df[hr_email_field].values:
                            exceptions.append({
                                'email': email,
                                'role': row.get('role_name', 'N/A'),
                                'action': 'revoke',
                                'pre_status': 'active',
                                'post_status': 'inactive'
                            })
                    
                    # Create exceptions DataFrame
                    reconciler.exceptions_df = pd.DataFrame(exceptions)
                    
                    # Store results
                    st.session_state.reconciliation_results = reconciler.exceptions_df
                    st.session_state.primary_upload_complete = True
                    st.success("Reconciliation completed successfully!")
                    
                    # Switch to Secondary Data Upload tab
                    st.session_state.current_tab = "Secondary Data Upload"
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Error during reconciliation: {str(e)}")

    with tab2:
        st.header("Secondary Data Upload")
        
        # Check if primary upload is complete
        if not st.session_state.primary_upload_complete:
            st.warning("Please complete the Primary Data Upload first.")
            st.stop()
        
        # Additional Data Upload
        additional_files = st.file_uploader("Upload Additional Data (CSV/Excel)", type=['csv', 'xlsx'], accept_multiple_files=True)
        
        if additional_files:
            st.session_state.additional_data = {}
            for file in additional_files:
                try:
                    df = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
                    # Reset index to start from 1 and rename it to S.No.
                    df.index = range(1, len(df) + 1)
                    df.index.name = 'S.No.'
                    st.session_state.additional_data[file.name] = df
                    st.success(f"Successfully loaded {file.name} with {len(df)} records")
                    
                    # Show field matching interface for each uploaded file
                    st.subheader(f"Field Mapping for {file.name}")
                    
                    # Get the final report columns from ReportFormats
                    report_formats = ReportFormats()
                    final_columns = report_formats.USER_LEVEL_COLUMNS
                    
                    # Create a mapping interface for each final column
                    st.write("Map your data columns to the final report columns:")
                    col1, col2 = st.columns(2)
                    
                    # Initialize field mappings in session state if not exists
                    if 'additional_field_mappings' not in st.session_state:
                        st.session_state.additional_field_mappings = {}
                    if file.name not in st.session_state.additional_field_mappings:
                        st.session_state.additional_field_mappings[file.name] = {}
                    
                    # Create mapping interface
                    with col1:
                        st.write("Final Report Column")
                        for col in final_columns:
                            st.write(f"- {col}")
                    
                    with col2:
                        st.write("Your Data Column")
                        for col in final_columns:
                            selected_col = st.selectbox(
                                f"Map to {col}",
                                options=[''] + list(df.columns),
                                key=f"{file.name}_{col}",
                                index=0
                            )
                            if selected_col:
                                st.session_state.additional_field_mappings[file.name][col] = selected_col
                    
                    # Show preview of mapped data
                    if st.session_state.additional_field_mappings[file.name]:
                        st.subheader("Preview of Mapped Data")
                        preview_df = df.copy()
                        # Rename columns based on mapping
                        rename_dict = {v: k for k, v in st.session_state.additional_field_mappings[file.name].items()}
                        preview_df = preview_df.rename(columns=rename_dict)
                        st.dataframe(preview_df)
                        
                except Exception as e:
                    st.error(f"Error loading {file.name}: {str(e)}")
        
        # Next button to proceed to Data Mapping section
        if st.button("Next", type="primary"):
            st.session_state.current_tab = "Data Mapping"
            st.experimental_rerun()

    with tab3:
        st.header("Data Mapping")
        
        if 'hr_data' in st.session_state and 'app_data' in st.session_state:
            # Field Mapping Interface
            st.subheader("Configure Field Mappings")
            
            # Initialize field mappings in session state if not exists
            if 'field_mappings' not in st.session_state:
                st.session_state.field_mappings = {}

            # Create mapping interface
            col1, col2 = st.columns(2)
            with col1:
                source_field = st.selectbox("Source Field", options=st.session_state.app_data.columns.tolist())
            with col2:
                target_field = st.selectbox("Target Field", options=st.session_state.app_data.columns.tolist())

            if st.button("Add Mapping"):
                st.session_state.field_mappings[source_field] = target_field
                st.success(f"Added mapping: {source_field} -> {target_field}")

            # Display current mappings with delete option
            if st.session_state.field_mappings:
                st.subheader("Current Field Mappings")
                for source, target in st.session_state.field_mappings.items():
                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        st.write(f"Source: {source}")
                    with col2:
                        st.write(f"Target: {target}")
                    with col3:
                        if st.button("Delete", key=f"delete_{source}"):
                            del st.session_state.field_mappings[source]
                            st.success(f"Deleted mapping: {source} -> {target}")
                            st.experimental_rerun()

            # Save mappings to database
            if st.button("Save Field Mappings"):
                try:
                    # Save mappings to database
                    for source, target in st.session_state.field_mappings.items():
                        db.store_field_mapping(source, target)
                    st.success("Field mappings saved successfully!")
                except Exception as e:
                    st.error(f"Error saving field mappings: {str(e)}")

    with tab4:
        st.header("Reconciliation Results")
        
        if st.session_state.reconciliation_results is not None:
            # Generate reconciliation ID
            recon_id = generate_reconciliation_id(st.session_state.selected_app)
            
            # Create a summary DataFrame with the specified columns
            summary_data = {
                'S.No.': [1],
                'Panel Name': [config_handler.get_app_name(st.session_state.selected_app)],
                'Reconciliation ID': [recon_id],
                'Reconciliation Month': [datetime.now().strftime('%B %Y')],
                'Status': ['Complete'],
                'Panel Data Uploaded By': ['System'],
                'Reconciliation Start Date': [datetime.now().strftime('%d-%m-%Y %H:%M:%S')],
                'Reconciliation Performed by': ['System'],
                'Reconciliation Completion Date': [datetime.now().strftime('%d-%m-%Y %H:%M:%S')],
                'Failure Reason': [''],
                'View Details': ['View']
            }
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.set_index('S.No.', inplace=True)
            
            # Add filter and export options above the table
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.subheader("Reconciliation Summary")
            with col2:
                # Filter options
                filter_type = st.selectbox(
                    "Filter by",
                    ["All", "Date", "Month"],
                    key="filter_type"
                )
                
                if filter_type == "Date":
                    selected_date = st.date_input("Select Date", datetime.now())
                    filter_date = selected_date.strftime('%d-%m-%Y')
                elif filter_type == "Month":
                    selected_month = st.date_input("Select Month", datetime.now())
                    filter_date = selected_month.strftime('%m-%Y')
            with col3:
                # Export options
                export_format = st.selectbox(
                    "Export as",
                    ["View", "Download CSV", "Download PDF"],
                    key="export_format"
                )
                
                if export_format == "Download CSV":
                    csv = summary_df.to_csv(index=True)
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name=f"reconciliation_summary_{recon_id}.csv",
                        mime="text/csv"
                    )
                elif export_format == "Download PDF":
                    # TODO: Implement PDF export
                    st.info("PDF export coming soon!")
            
            # Display the summary table
            st.dataframe(summary_df)
            
            # Add disclaimer
            st.info("Disclaimer: Only active users considered for Reconciliation activity")
            
            # Store the reconciliation ID in session state
            st.session_state.reconciliation_id = recon_id
        else:
            st.info("No reconciliation results available. Please complete the reconciliation process first.")

    with tab5:
        st.header("Reports")
        
        # Create two columns for the tables
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("PANEL LEVEL REPORT - FOR IT / AUDIT TEAM")
            
            # Sample data for panel level report
            panel_data = {
                'Panel Name': ['Seller Panel', 'BOSS Panel'],
                'Total Users': [100, 150],
                'Reconciliation ID': ['RCN_SP_001', 'RCN_BP_001'],
                'Reconciliation Date': ['15-03-2024', '15-03-2024'],
                'Active': [80, 120],
                'Inactive': [15, 20],
                'Others (Not Found)': [5, 10],
                'Service IDs': [0, 0],
                'Third Party Users': [10, 15],
                'Group Entity': [5, 8],
                'Vendor / Auditor / Consultant': [3, 5],
                'Entity Movement': [2, 3],
                'Incorrect Email ID': [1, 2],
                'Dual Accounts': [0, 1],
                'Others': [2, 3]
            }
            
            panel_df = pd.DataFrame(panel_data)
            # Reset index to start from 1 and rename it to S.No.
            panel_df.index = range(1, len(panel_df) + 1)
            panel_df.index.name = 'S.No.'
            
            # Display the panel level report
            st.dataframe(panel_df)
            
            # Add download button for each row
            for idx, row in panel_df.iterrows():
                if st.button(f"Download CSV - {row['Panel Name']}", key=f"panel_download_{idx}"):
                    csv = pd.DataFrame([row]).to_csv(index=False)
                    st.download_button(
                        label=f"Download {row['Panel Name']} Report",
                        data=csv,
                        file_name=f"panel_report_{row['Panel Name'].replace(' ', '_')}_{row['Reconciliation ID']}.csv",
                        mime="text/csv",
                        key=f"panel_download_btn_{idx}"
                    )
        
        with col2:
            st.subheader("USER LEVEL REPORT - FOR IT / AUDIT TEAM")
            
            # Sample data for user level report
            user_data = {
                'User Email ID': ['user1@example.com', 'user2@example.com', 'user3@example.com'],
                'Panel Name': ['Seller Panel', 'BOSS Panel', 'Seller Panel'],
                'Pre Recon Status': ['Active', 'Inactive', 'Active'],
                'Date of Reconciliation': ['15-03-2024', '15-03-2024', '15-03-2024'],
                'Post Recon Status': ['Active', 'Inactive', 'Inactive']
            }
            
            user_df = pd.DataFrame(user_data)
            # Reset index to start from 1 and rename it to S.No.
            user_df.index = range(1, len(user_df) + 1)
            user_df.index.name = 'S.No.'
            
            # Display the user level report
            st.dataframe(user_df)
            
            # Add download button for the entire user level report
            if st.button("Download User Level Report", key="user_download"):
                csv = user_df.to_csv(index=True)
                st.download_button(
                    label="Download User Level Report",
                    data=csv,
                    file_name=f"user_level_report_{datetime.now().strftime('%d%m%Y')}.csv",
                    mime="text/csv",
                    key="user_download_btn"
                )

    with tab6:
        st.header("Audit Trails")
        
        # Display audit trail
        if st.session_state.audit_trail:
            st.subheader("Recent Activities")
            for activity in st.session_state.audit_trail:
                st.write(f"- {activity}")
        else:
            st.info("No audit trail available yet.")

    with tab7:
        st.header("File Upload History")
        
        if st.session_state.upload_history:
            # Convert upload history to DataFrame
            history_df = pd.DataFrame(st.session_state.upload_history)
            # Reset index to start from 1 and rename it to S.No.
            history_df.index = range(1, len(history_df) + 1)
            history_df.index.name = 'S.No.'
            
            # Display the history table
            st.dataframe(history_df)
            
            # Add download button for the history
            if st.button("Download Upload History", key="history_download"):
                csv = history_df.to_csv(index=True)
                st.download_button(
                    label="Download Upload History",
                    data=csv,
                    file_name=f"upload_history_{datetime.now().strftime('%d%m%Y')}.csv",
                    mime="text/csv",
                    key="history_download_btn"
                )
        else:
            st.info("No file upload history available yet.")

if __name__ == "__main__":
    main() 