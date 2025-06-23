import json
import logging
from typing import Dict, Any, List, Tuple
import os
import pandas as pd

logger = logging.getLogger(__name__)

class ConfigHandler:
    def __init__(self, config_path: str = None):
        """Initialize the configuration handler.
        
        Args:
            config_path (str, optional): Path to the JSON configuration file.
                If not provided, will look for config in default location.
        """
        if config_path is None:
            # Default config path relative to the script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(script_dir, "config", "app_reconciliation_config.json")
        
        self.config_path = config_path
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load the JSON configuration file.
        
        Returns:
            Dict[str, Any]: The loaded configuration
        """
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            raise
            
    def get_app_config(self, app_name: str) -> Dict[str, Any]:
        """Get configuration for a specific application.
        
        Args:
            app_name (str): Name of the application
            
        Returns:
            Dict[str, Any]: Application configuration
        """
        if app_name not in self.config:
            raise ValueError(f"Configuration not found for application: {app_name}")
        return self.config[app_name]
    
    def get_app_name(self, app_id: str) -> str:
        """Get the display name of an application.
        
        Args:
            app_id (str): Application identifier
            
        Returns:
            str: Application display name
        """
        app_config = self.get_app_config(app_id)
        return app_config.get('name', app_id)
    
    def get_app_description(self, app_id: str) -> str:
        """Get the description of an application.
        
        Args:
            app_id (str): Application identifier
            
        Returns:
            str: Application description
        """
        app_config = self.get_app_config(app_id)
        return app_config.get('description', '')
    
    def get_source_path(self, app_name: str, source_type: str) -> str:
        """Get the fixed path for a data source.
        
        Args:
            app_name (str): Name of the application
            source_type (str): Type of source (e.g., 'HR_Data', 'SellerPanel_Data')
            
        Returns:
            str: Path to the data source file
        """
        app_config = self.get_app_config(app_name)
        if 'SOT' not in app_config or source_type not in app_config['SOT']:
            raise ValueError(f"Source type {source_type} not found in configuration for {app_name}")
        return app_config['SOT'][source_type]['path']
    
    def get_table_format(self, app_name: str, source_type: str) -> Dict[str, Any]:
        """Get the table format configuration for a source type.
        
        Args:
            app_name (str): Name of the application
            source_type (str): Type of source
            
        Returns:
            Dict[str, Any]: Table format configuration
        """
        app_config = self.get_app_config(app_name)
        if 'SOT' not in app_config or source_type not in app_config['SOT']:
            raise ValueError(f"Source type {source_type} not found in configuration for {app_name}")
        return app_config['SOT'][source_type]['table_format']
    
    def validate_file_format(self, app_name: str, source_type: str, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """Validate if a DataFrame matches the required format.
        
        Args:
            app_name (str): Name of the application
            source_type (str): Type of source
            df (pd.DataFrame): DataFrame to validate
            
        Returns:
            Tuple[bool, List[str]]: (is_valid, list of error messages)
        """
        table_format = self.get_table_format(app_name, source_type)
        required_columns = table_format['required_columns']
        errors = []
        
        # Check for missing columns
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            errors.append(f"Missing required columns: {', '.join(missing_columns)}")
        
        # Check for extra columns
        extra_columns = [col for col in df.columns if col not in required_columns]
        if extra_columns:
            errors.append(f"Extra columns found: {', '.join(extra_columns)}")
        
        return len(errors) == 0, errors
    
    def get_source_mappings(self, app_name: str, source_type: str) -> Dict[str, str]:
        """Get field mappings for a specific source type.
        
        Args:
            app_name (str): Name of the application
            source_type (str): Type of source
            
        Returns:
            Dict[str, str]: Field mappings for the source
        """
        app_config = self.get_app_config(app_name)
        if 'SOT' not in app_config or source_type not in app_config['SOT']:
            raise ValueError(f"Source type {source_type} not found in configuration for {app_name}")
        return app_config['SOT'][source_type]['mappings']
    
    def get_unified_field(self, app_name: str, source_type: str, field_name: str) -> str:
        """Get the unified field name for a source field.
        
        Args:
            app_name (str): Name of the application
            source_type (str): Type of source
            field_name (str): Name of the field in the source
            
        Returns:
            str: Unified field name
        """
        mappings = self.get_source_mappings(app_name, source_type)
        if field_name not in mappings:
            raise ValueError(f"Field {field_name} not found in mappings for {app_name} {source_type}")
        return mappings[field_name]
    
    def get_required_fields(self, app_name: str, source_type: str) -> List[str]:
        """Get list of required fields for a source type.
        
        Args:
            app_name (str): Name of the application
            source_type (str): Type of source
            
        Returns:
            List[str]: List of required field names
        """
        table_format = self.get_table_format(app_name, source_type)
        return table_format['required_columns']
    
    def get_column_display_names(self, app_name: str, source_type: str) -> Dict[str, str]:
        """Get display names for columns.
        
        Args:
            app_name (str): Name of the application
            source_type (str): Type of source
            
        Returns:
            Dict[str, str]: Mapping of column names to display names
        """
        table_format = self.get_table_format(app_name, source_type)
        return table_format['column_display_names']
    
    def get_status_mapping(self, app_name: str, source_type: str) -> Dict[str, List[str]]:
        """Get status mapping for a source type.
        
        Args:
            app_name (str): Name of the application
            source_type (str): Type of source
            
        Returns:
            Dict[str, List[str]]: Status mapping dictionary
        """
        app_config = self.get_app_config(app_name)
        if 'validation' not in app_config or 'status_mapping' not in app_config['validation']:
            return {}
        return app_config['validation']['status_mapping'].get(source_type, {})
    
    def get_report_levels(self, app_name: str) -> Dict[str, Dict[str, Any]]:
        """Get report level configurations.
        
        Args:
            app_name (str): Name of the application
            
        Returns:
            Dict[str, Dict[str, Any]]: Report level configurations
        """
        app_config = self.get_app_config(app_name)
        return app_config.get('report_levels', {})
    
    def get_all_apps(self) -> List[str]:
        """Get list of all configured applications.
        
        Returns:
            List[str]: List of application identifiers
        """
        return list(self.config.keys())
    
    def get_all_apps_with_names(self) -> Dict[str, str]:
        """Get dictionary of all applications with their display names.
        
        Returns:
            Dict[str, str]: Dictionary mapping app IDs to display names
        """
        return {app_id: self.get_app_name(app_id) for app_id in self.get_all_apps()}
    
    def get_email_mapping(self, app_name: str):
        app_config = self.get_app_config(app_name)
        if 'SOT' not in app_config or 'HR_Data' not in app_config['SOT']:
            raise ValueError(f"HR data configuration not found for {app_name}")
        return app_config['SOT']['HR_Data']
    
    def get_hr_email_column(self, app_name: str) -> str:
        """Get the HR email column name."""
        mapping = self.get_email_mapping(app_name)
        return list(mapping.keys())[0]
    
    def get_panel_email_column(self, app_name: str) -> str:
        """Get the panel email column name."""
        mapping = self.get_email_mapping(app_name)
        return list(mapping.values())[0] 