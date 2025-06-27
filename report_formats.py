from datetime import datetime
from typing import Dict, List

class ReportFormats:
    # Standard column names for reconciliation summary
    RECON_SUMMARY_COLUMNS = [
        "Recon ID",
        "Panel Name",
        "Recon Status",
        "Reconciliation Timestamp",
        "Total Users Reviewed",
        "Revoke Access",
        "Retain Access",
        "Comment/Remarks"
    ]

    # Standard column names for user level report
    USER_LEVEL_COLUMNS = [
        "User Email ID",
        "Panel Name",
        "Pre Recon Status",
        "Date of Reconciliation",
        "Post Recon Status"
    ]

    # Standard status values
    RECON_STATUS = {
        "COMPLETED": "Completed",
        "PENDING": "Pending",
        "FAILED": "Failed"
    }

    # Standard email for discrepancies
    SUPPORT_EMAIL = "manish1.taneja@paytm.com"

    @staticmethod
    def get_report_header(app_name: str, source_file: str) -> Dict:
        return {
            "title": "User Access Reconciliation Report",
            "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "source_of_truth": source_file,
            "app_name": app_name,
            "support_email": ReportFormats.SUPPORT_EMAIL
        }

    @staticmethod
    def get_recon_summary_row(
        recon_id: str,
        panel_name: str,
        total_users: int,
        revoke_count: int,
        retain_count: int,
        status: str = "Completed",
        comments: str = ""
    ) -> Dict:
        return {
            "Recon ID": recon_id,
            "Panel Name": panel_name,
            "Recon Status": status,
            "Reconciliation Timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "Total Users Reviewed": total_users,
            "Revoke Access": revoke_count,
            "Retain Access": retain_count,
            "Comment/Remarks": comments
        }

    @staticmethod
    def get_user_level_row(
        email: str,
        panel_name: str,
        pre_status: str,
        post_status: str
    ) -> Dict:
        return {
            "User Email ID": email,
            "Panel Name": panel_name,
            "Pre Recon Status": pre_status,
            "Date of Reconciliation": datetime.now().strftime("%d/%m/%Y"),
            "Post Recon Status": post_status
        }

class ProcessTableFormat:
    """Standard format for process table structure."""
    
    COLUMNS = [
        "Process ID",
        "Application",
        "Start Time",
        "End Time",
        "Status",
        "Total Records",
        "Processed Records",
        "Failed Records",
        "Action Taken",
        "Remarks"
    ]
    
    STATUS_VALUES = {
        "IN_PROGRESS": "In Progress",
        "COMPLETED": "Completed",
        "FAILED": "Failed",
        "CANCELLED": "Cancelled"
    }
    
    @staticmethod
    def get_process_row(
        process_id: str,
        application: str,
        start_time: datetime,
        end_time: datetime = None,
        status: str = "IN_PROGRESS",
        total_records: int = 0,
        processed_records: int = 0,
        failed_records: int = 0,
        action_taken: str = "",
        remarks: str = ""
    ) -> Dict:
        return {
            "Process ID": process_id,
            "Application": application,
            "Start Time": start_time.strftime("%d/%m/%Y %H:%M:%S"),
            "End Time": end_time.strftime("%d/%m/%Y %H:%M:%S") if end_time else "",
            "Status": ProcessTableFormat.STATUS_VALUES.get(status, status),
            "Total Records": total_records,
            "Processed Records": processed_records,
            "Failed Records": failed_records,
            "Action Taken": action_taken,
            "Remarks": remarks
        }

class OverallReconciliationStatusSummary:
    """Report 1: OVERALL RECONCILIATION STATUS SUMMARY"""
    
    COLUMNS = [
        "S.No.",
        "Panel Name",
        "Reconciliation ID",
        "Reconciliation Month",
        "Status",
        "Panel Data Uploaded By",
        "Reconciliation Start Date",
        "Reconciliation Performed by",
        "Reconciliation Completion Date",
        "Failure Reason",
        "View Details"
    ]
    
    @staticmethod
    def get_summary_row(
        panel_name: str,
        recon_id: str,
        status: str = "Complete",
        uploaded_by: str = "System",
        performed_by: str = "System",
        failure_reason: str = ""
    ) -> Dict:
        return {
            "S.No.": 1,
            "Panel Name": panel_name,
            "Reconciliation ID": recon_id,
            "Reconciliation Month": datetime.now().strftime('%B %Y'),
            "Status": status,
            "Panel Data Uploaded By": uploaded_by,
            "Reconciliation Start Date": datetime.now().strftime('%d-%m-%Y %H:%M:%S'),
            "Reconciliation Performed by": performed_by,
            "Reconciliation Completion Date": datetime.now().strftime('%d-%m-%Y %H:%M:%S'),
            "Failure Reason": failure_reason,
            "View Details": "View"
        }

class PanelWiseReconciliationSummary:
    """Report 2: PANEL WISE RECONCILIATION SUMMARY"""
    
    COLUMNS = [
        "Panel Name",
        "Total Users",
        "Reconciliation ID",
        "Reconciliation Date",
        "Active",
        "Inactive",
        "Others (Not Found)",
        "Service IDs",
        "Third Party Users",
        "Group Entity",
        "Vendor / Auditor / Consultant",
        "Entity Movement",
        "Incorrect Email ID",
        "Dual Accounts",
        "Others"
    ]
    
    @staticmethod
    def get_panel_summary_row(
        panel_name: str,
        total_users: int,
        recon_id: str,
        active_count: int = 0,
        inactive_count: int = 0,
        not_found_count: int = 0,
        service_ids: int = 0,
        third_party_users: int = 0,
        group_entity: int = 0,
        vendor_auditor_consultant: int = 0,
        entity_movement: int = 0,
        incorrect_email: int = 0,
        dual_accounts: int = 0,
        others: int = 0
    ) -> Dict:
        return {
            "Panel Name": panel_name,
            "Total Users": total_users,
            "Reconciliation ID": recon_id,
            "Reconciliation Date": datetime.now().strftime('%d-%m-%Y'),
            "Active": active_count,
            "Inactive": inactive_count,
            "Others (Not Found)": not_found_count,
            "Service IDs": service_ids,
            "Third Party Users": third_party_users,
            "Group Entity": group_entity,
            "Vendor / Auditor / Consultant": vendor_auditor_consultant,
            "Entity Movement": entity_movement,
            "Incorrect Email ID": incorrect_email,
            "Dual Accounts": dual_accounts,
            "Others": others
        }

class IndividualPanelWiseDetailedReport:
    """Report 3: INDIVIDUAL PANEL WISE DETAILED REPORT"""
    
    COLUMNS = [
        "S.No.",
        "User Email ID",
        "Panel Name",
        "User Status",
        "HR Status",
        "Reconciliation Status",
        "Action Required",
        "Reconciliation Date",
        "Remarks"
    ]
    
    @staticmethod
    def get_detailed_row(
        email: str,
        panel_name: str,
        user_status: str,
        hr_status: str,
        recon_status: str,
        action_required: str,
        remarks: str = ""
    ) -> Dict:
        return {
            "S.No.": 1,
            "User Email ID": email,
            "Panel Name": panel_name,
            "User Status": user_status,
            "HR Status": hr_status,
            "Reconciliation Status": recon_status,
            "Action Required": action_required,
            "Reconciliation Date": datetime.now().strftime('%d-%m-%Y'),
            "Remarks": remarks
        }

class UserWiseSummary:
    """Report 4: USER-WISE SUMMARY"""
    
    COLUMNS = [
        "S.No.",
        "User Email ID",
        "Panel Name",
        "Pre Recon Status",
        "Date of Reconciliation",
        "Post Recon Status",
        "Status Change",
        "Action Taken",
        "Comments"
    ]
    
    @staticmethod
    def get_user_summary_row(
        email: str,
        panel_name: str,
        pre_status: str,
        post_status: str,
        action_taken: str = "",
        comments: str = ""
    ) -> Dict:
        status_change = "No Change" if pre_status == post_status else f"{pre_status} → {post_status}"
        return {
            "S.No.": 1,
            "User Email ID": email,
            "Panel Name": panel_name,
            "Pre Recon Status": pre_status,
            "Date of Reconciliation": datetime.now().strftime('%d-%m-%Y'),
            "Post Recon Status": post_status,
            "Status Change": status_change,
            "Action Taken": action_taken,
            "Comments": comments
        } 