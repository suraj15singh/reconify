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
        st.session_state.current_tab = "HR and App Data"
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
        "HR and App Data", 
        "Supplementary Info", 
        "Data Mapping", 
        "Reconciliation Results", 
        "Reports",
        "Audit Trails",
        "File Upload History"
    ])

    with tab1:
        st.header("HR and App Data")
        
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
        
        # Logic to handle new file upload and reset state
        if app_file and (st.session_state.get('app_file_name') != app_file.name):
            st.session_state.app_file_name = app_file.name
            # Reset states for new file
            for key in ['raw_app_data', 'app_data', 'selected_columns']:
                if key in st.session_state:
                    del st.session_state[key]

        # If file is present but not processed
        if app_file and 'app_data' not in st.session_state:
            # Load data if not already in session state
            if 'raw_app_data' not in st.session_state:
                try:
                    if app_file.name.endswith('.csv'):
                        st.session_state.raw_app_data = pd.read_csv(app_file)
                    else:
                        # For Excel files, explicitly read only the first sheet (sheet_name=0)
                        st.session_state.raw_app_data = pd.read_excel(app_file, sheet_name=0)
                except Exception as e:
                    st.error(f"Error loading Application data: {str(e)}")
                    st.stop()

            st.subheader("Select columns to ingest")
            with st.form(key='column_selection_form'):
                all_columns = st.session_state.raw_app_data.columns.tolist()
                
                selected_columns = st.multiselect(
                    "Select the columns you want to ingest from the uploaded file:",
                    options=all_columns,
                    default=all_columns
                )
                
                submitted = st.form_submit_button("Ingest Selected Columns")
                if submitted:
                    st.session_state.selected_columns = selected_columns
                    
                    try:
                        app_df = st.session_state.raw_app_data[st.session_state.selected_columns].copy()
                        
                        # Verify required fields exist
                        if selected_app and 'SOT' in config_handler.get_app_config(selected_app):
                            required_field = config_handler.get_app_config(selected_app)['SOT']['HR_Data']['Official Email Address']
                            if required_field not in app_df.columns:
                                st.error(f"Required field '{required_field}' not found in the selected columns. Please make sure it is selected and press 'Ingest' again.")
                                st.stop()
                        
                        # ----- SUCCESSFUL INGESTION -----
                        app_df.index = range(1, len(app_df) + 1)
                        app_df.index.name = 'S.No.'
                        if 'L1 Manager Code' in app_df.columns:
                            app_df['L1 Manager Code'] = app_df['L1 Manager Code'].astype(str).str.replace(',', '')
                        
                        st.session_state.app_data = app_df
                        
                        st.session_state.upload_history.append({
                            'timestamp': datetime.now().strftime('%d-%m-%Y %H:%M:%S'),
                            'file_type': 'Application Data',
                            'file_name': app_file.name,
                            'records': len(app_df),
                            'application': available_apps[selected_app]
                        })
                        st.experimental_rerun()

                    except Exception as e:
                        st.error(f"Error processing Application data: {str(e)}")

        # If data is ingested, show it
        if 'app_data' in st.session_state:
            st.success(f"Successfully loaded Application data with {len(st.session_state.app_data)} records")
            st.write("Preview of Application Data:")
            st.dataframe(st.session_state.app_data)

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
                    
                    # Switch to Supplementary Info tab
                    st.session_state.current_tab = "Supplementary Info"
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Error during reconciliation: {str(e)}")

    with tab2:
        st.header("Supplementary Info")
        
        # Check if primary upload is complete
        if not st.session_state.primary_upload_complete:
            st.warning("Please complete the HR and App Data upload first.")
            st.stop()
        
        # Additional Data Upload
        additional_files = st.file_uploader("Upload Additional Data (CSV/Excel)", type=['csv', 'xlsx'], accept_multiple_files=True)
        
        if additional_files:
            st.session_state.additional_data = {}
            for file in additional_files:
                try:
                    if file.name.endswith('.csv'):
                        df = pd.read_csv(file)
                    else:
                        # For Excel files, explicitly read only the first sheet (sheet_name=0)
                        df = pd.read_excel(file, sheet_name=0)
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
        
        # App selection dropdown at the top of Data Mapping
        config_handler = ConfigHandler()
        available_apps = config_handler.get_all_apps_with_names()
        # Pre-select from session if available
        default_app = st.session_state.get('selected_app') if st.session_state.get('selected_app') in available_apps else None
        selected_mapping_app = st.selectbox(
            "Select Application for Mapping",
            options=list(available_apps.keys()),
            format_func=lambda x: available_apps[x],
            index=list(available_apps.keys()).index(default_app) if default_app else 0,
            key="mapping_app_selectbox"
        )
        if selected_mapping_app:
            st.session_state.selected_app = selected_mapping_app
            st.info(f"Selected Application for Mapping: {available_apps[selected_mapping_app]}")
            st.write(f"Description: {config_handler.get_app_description(selected_mapping_app)}")
        
        # Only show mapping interface for the selected app
        if (
            'hr_data' in st.session_state and 
            'app_data' in st.session_state and 
            st.session_state.selected_app == selected_mapping_app
        ):
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
            col1, col2 = st.columns([2, 1])
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
        
        # Create tabs for the 4 different reports
        report_tab1, report_tab2, report_tab3, report_tab4 = st.tabs([
            "Overall Reconciliation Status Summary",
            "Panel Wise Reconciliation Summary", 
            "Individual Panel Wise Detailed Report",
            "User-Wise Summary"
        ])
        
        with report_tab1:
            st.subheader("OVERALL RECONCILIATION STATUS SUMMARY")
            
            if st.session_state.reconciliation_results is not None:
                # Generate reconciliation ID
                recon_id = generate_reconciliation_id(st.session_state.selected_app)
                
                # Create summary data using the new format
                from report_formats import OverallReconciliationStatusSummary
                summary_data = OverallReconciliationStatusSummary.get_summary_row(
                    panel_name=config_handler.get_app_name(st.session_state.selected_app),
                    recon_id=recon_id
                )
                
                summary_df = pd.DataFrame([summary_data])
                summary_df.set_index('S.No.', inplace=True)
                
                # Add filter and export options
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.write("**Reconciliation Summary**")
                with col2:
                    filter_type = st.selectbox(
                        "Filter by",
                        ["All", "Date", "Month"],
                        key="overall_filter_type"
                    )
                    if filter_type == "Date":
                        selected_date = st.date_input("Select Date", datetime.now())
                        filter_date = selected_date.strftime('%d-%m-%Y')
                    elif filter_type == "Month":
                        selected_month = st.date_input("Select Month", datetime.now())
                        filter_date = selected_month.strftime('%m-%Y')
                
                # Display the summary table
                st.dataframe(summary_df)
                st.info("Disclaimer: Only active users considered for Reconciliation activity")
            else:
                st.info("No reconciliation results available. Please complete the reconciliation process first.")
        
        with report_tab2:
            st.subheader("PANEL WISE RECONCILIATION SUMMARY")
            
            # Sample data for panel wise reconciliation summary
            from report_formats import PanelWiseReconciliationSummary
            
            panel_summary_data = [
                PanelWiseReconciliationSummary.get_panel_summary_row(
                    panel_name="Seller Panel",
                    total_users=100,
                    recon_id="RCN_SP_001",
                    active_count=80,
                    inactive_count=15,
                    not_found_count=5,
                    service_ids=0,
                    third_party_users=10,
                    group_entity=5,
                    vendor_auditor_consultant=3,
                    entity_movement=2,
                    incorrect_email=1,
                    dual_accounts=0,
                    others=2
                ),
                PanelWiseReconciliationSummary.get_panel_summary_row(
                    panel_name="BOSS Panel",
                    total_users=150,
                    recon_id="RCN_BP_001",
                    active_count=120,
                    inactive_count=20,
                    not_found_count=10,
                    service_ids=0,
                    third_party_users=15,
                    group_entity=8,
                    vendor_auditor_consultant=5,
                    entity_movement=3,
                    incorrect_email=2,
                    dual_accounts=1,
                    others=3
                )
            ]
            
            panel_summary_df = pd.DataFrame(panel_summary_data)
            panel_summary_df.index = range(1, len(panel_summary_df) + 1)
            panel_summary_df.index.name = 'S.No.'
            
            # Add filter and export options
            col1, col2 = st.columns([2, 1])
            with col1:
                st.write("**Panel Wise Summary**")
            with col2:
                panel_filter = st.selectbox(
                    "Filter by Panel",
                    ["All Panels"] + list(panel_summary_df['Panel Name'].unique()),
                    key="panel_filter"
                )
            
            # Display filtered data
            if panel_filter != "All Panels":
                filtered_df = panel_summary_df[panel_summary_df['Panel Name'] == panel_filter]
                st.dataframe(filtered_df)
            else:
                st.dataframe(panel_summary_df)
        
        with report_tab3:
            st.subheader("INDIVIDUAL PANEL WISE DETAILED REPORT")
            
            # Sample data for individual panel wise detailed report
            from report_formats import IndividualPanelWiseDetailedReport
            
            detailed_data = [
                IndividualPanelWiseDetailedReport.get_detailed_row(
                    email="user1@example.com",
                    panel_name="Seller Panel",
                    user_status="Active",
                    hr_status="Active",
                    recon_status="Matched",
                    action_required="No Action",
                    remarks="User status matches HR data"
                ),
                IndividualPanelWiseDetailedReport.get_detailed_row(
                    email="user2@example.com",
                    panel_name="Seller Panel",
                    user_status="Active",
                    hr_status="Inactive",
                    recon_status="Mismatch",
                    action_required="Revoke Access",
                    remarks="User is inactive in HR but active in panel"
                ),
                IndividualPanelWiseDetailedReport.get_detailed_row(
                    email="user3@example.com",
                    panel_name="BOSS Panel",
                    user_status="Inactive",
                    hr_status="Active",
                    recon_status="Mismatch",
                    action_required="Activate Access",
                    remarks="User is active in HR but inactive in panel"
                )
            ]
            
            detailed_df = pd.DataFrame(detailed_data)
            detailed_df.index = range(1, len(detailed_df) + 1)
            detailed_df.index.name = 'S.No.'
            
            # Add filter and export options
            col1, col2 = st.columns([2, 1])
            with col1:
                st.write("**Detailed Report**")
            with col2:
                detail_filter = st.selectbox(
                    "Filter by Panel",
                    ["All Panels"] + list(detailed_df['Panel Name'].unique()),
                    key="detail_filter"
                )
            
            # Display filtered data
            if detail_filter != "All Panels":
                filtered_detail_df = detailed_df[detailed_df['Panel Name'] == detail_filter]
                st.dataframe(filtered_detail_df)
            else:
                st.dataframe(detailed_df)
        
        with report_tab4:
            st.subheader("USER-WISE SUMMARY")
            
            # Sample data for user-wise summary
            from report_formats import UserWiseSummary
            
            user_summary_data = [
                UserWiseSummary.get_user_summary_row(
                    email="user1@example.com",
                    panel_name="Seller Panel",
                    pre_status="Active",
                    post_status="Active",
                    action_taken="No Action",
                    comments="Status unchanged"
                ),
                UserWiseSummary.get_user_summary_row(
                    email="user2@example.com",
                    panel_name="Seller Panel",
                    pre_status="Active",
                    post_status="Inactive",
                    action_taken="Access Revoked",
                    comments="User inactive in HR data"
                ),
                UserWiseSummary.get_user_summary_row(
                    email="user3@example.com",
                    panel_name="BOSS Panel",
                    pre_status="Inactive",
                    post_status="Active",
                    action_taken="Access Activated",
                    comments="User active in HR data"
                )
            ]
            
            user_summary_df = pd.DataFrame(user_summary_data)
            user_summary_df.index = range(1, len(user_summary_df) + 1)
            user_summary_df.index.name = 'S.No.'
            
            # Add filter, search, and export options
            col1, col2 = st.columns([2, 1])
            with col1:
                st.write("**User Summary**")
                # User search input
                user_search = st.text_input("Search by User Email", "", key="user_search")
            with col2:
                user_filter = st.selectbox(
                    "Filter by Status Change",
                    ["All Changes", "No Change", "Active → Inactive", "Inactive → Active"],
                    key="user_filter"
                )
            
            # Apply search and filter
            filtered_user_df = user_summary_df
            if user_search:
                filtered_user_df = filtered_user_df[filtered_user_df['User Email ID'].str.contains(user_search, case=False, na=False)]
            if user_filter != "All Changes":
                if user_filter == "No Change":
                    filtered_user_df = filtered_user_df[filtered_user_df['Status Change'] == "No Change"]
                elif user_filter == "Active → Inactive":
                    filtered_user_df = filtered_user_df[filtered_user_df['Status Change'] == "Active → Inactive"]
                elif user_filter == "Inactive → Active":
                    filtered_user_df = filtered_user_df[filtered_user_df['Status Change'] == "Inactive → Active"]
            st.dataframe(filtered_user_df)

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