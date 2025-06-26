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