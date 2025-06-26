import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime
from dotenv import load_dotenv
import uuid
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class DatabaseHandler:
    def __init__(self):
        try:
            # Get database configuration from environment variables
            db_name = os.getenv('DB_NAME', 'reconify')
            db_user = os.getenv('DB_USER', 'postgres')
            db_password = os.getenv('DB_PASSWORD', 'postgres')
            db_host = os.getenv('DB_HOST', 'localhost')
            db_port = os.getenv('DB_PORT', '5432')

            # First try to connect to postgres database to check if our database exists
            self.conn = psycopg2.connect(
                dbname='postgres',
                user=db_user,
                password=db_password,
                host=db_host,
                port=db_port
            )
            self.conn.autocommit = True

            # Check if our database exists
            with self.conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
                if not cur.fetchone():
                    logger.info(f"Creating database {db_name}")
                    cur.execute(f"CREATE DATABASE {db_name}")
            
            # Close connection to postgres database
            self.conn.close()

            # Connect to our database
            self.conn = psycopg2.connect(
                dbname=db_name,
                user=db_user,
                password=db_password,
                host=db_host,
                port=db_port
            )
            self.conn.autocommit = True
            
            # Create tables
            self._create_tables()
            self._create_triggers()
            
            # Verify table structure
            self._verify_table_structure()
            
            logger.info("Successfully connected to database and initialized tables")
            
        except psycopg2.OperationalError as e:
            logger.error(f"Database connection error: {str(e)}")
            raise Exception(
                "Could not connect to database. Please ensure PostgreSQL is running and "
                "the database configuration in .env file is correct."
            )
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            raise

    def _create_tables(self):
        """Create necessary tables if they don't exist."""
        with self.conn.cursor() as cur:
            # Create applications table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create employees table with enhanced status tracking
            cur.execute("""
                CREATE TABLE IF NOT EXISTS employees (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    first_name VARCHAR(100),
                    last_name VARCHAR(100),
                    manager_email VARCHAR(255),
                    department VARCHAR(100),
                    employee_type VARCHAR(50),
                    employment_status VARCHAR(50) DEFAULT 'Active',
                    last_hr_update TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create app_users table with enhanced status tracking
            cur.execute("""
                CREATE TABLE IF NOT EXISTS app_users (
                    id SERIAL PRIMARY KEY,
                    employee_id INTEGER REFERENCES employees(id),
                    application_id INTEGER REFERENCES applications(id),
                    role_name VARCHAR(100),
                    status VARCHAR(50) DEFAULT 'Active',
                    service_id VARCHAR(100),
                    h_id VARCHAR(100),
                    last_access TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(employee_id, application_id)
                )
            """)

            # Create data_snapshots table for reconciliation runs
            cur.execute("""
                CREATE TABLE IF NOT EXISTS data_snapshots (
                    id SERIAL PRIMARY KEY,
                    snapshot_type VARCHAR(50) NOT NULL,
                    source_name VARCHAR(255) NOT NULL,
                    version VARCHAR(50) NOT NULL,
                    data JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by VARCHAR(255) NOT NULL
                )
            """)

            # Create reconciliation_runs table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS reconciliation_runs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    run_name VARCHAR(255) NOT NULL,
                    description TEXT,
                    reconciliation_type VARCHAR(50) NOT NULL,
                    hr_data_source VARCHAR(255) NOT NULL,
                    panel_data_sources TEXT[] NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    status VARCHAR(50) NOT NULL,
                    initiated_by_user_id VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create reconciliation_results table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS reconciliation_results (
                    id SERIAL PRIMARY KEY,
                    reconciliation_run_id UUID REFERENCES reconciliation_runs(id),
                    employee_id INTEGER REFERENCES employees(id),
                    application_id INTEGER REFERENCES applications(id),
                    hr_status VARCHAR(50),
                    app_status VARCHAR(50),
                    reconciliation_status VARCHAR(100),
                    recommended_action VARCHAR(100),
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create data_change_logs table for detailed audit trail
            cur.execute("""
                CREATE TABLE IF NOT EXISTS data_change_logs (
                    id SERIAL PRIMARY KEY,
                    table_name VARCHAR(100) NOT NULL,
                    record_id VARCHAR(100) NOT NULL,
                    field_name VARCHAR(100) NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    changed_by VARCHAR(255) NOT NULL,
                    change_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    change_reason TEXT,
                    reconciliation_run_id UUID REFERENCES reconciliation_runs(id)
                )
            """)

            # Create indexes for better query performance
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_employees_email ON employees(email);
                CREATE INDEX IF NOT EXISTS idx_employees_status ON employees(employment_status);
                CREATE INDEX IF NOT EXISTS idx_app_users_status ON app_users(status);
                CREATE INDEX IF NOT EXISTS idx_data_change_logs_record ON data_change_logs(table_name, record_id);
                CREATE INDEX IF NOT EXISTS idx_data_snapshots_type_version ON data_snapshots(snapshot_type, version);
            """)

    def _create_triggers(self):
        """Create triggers for automatic audit logging."""
        with self.conn.cursor() as cur:
            try:
                # Create function for logging changes
                cur.execute("""
                    CREATE OR REPLACE FUNCTION log_data_changes()
                    RETURNS TRIGGER AS $$
                    DECLARE
                        col_name text;
                        old_val text;
                        new_val text;
                    BEGIN
                        IF TG_OP = 'UPDATE' THEN
                            FOR col_name IN 
                                SELECT column_name 
                                FROM information_schema.columns 
                                WHERE table_name = TG_TABLE_NAME
                            LOOP
                                EXECUTE format('SELECT ($1).%I::text, ($2).%I::text', col_name, col_name)
                                    INTO old_val, new_val
                                    USING OLD, NEW;
                                
                                IF old_val IS DISTINCT FROM new_val THEN
                                    INSERT INTO data_change_logs (
                                        table_name, record_id, field_name, 
                                        old_value, new_value, changed_by
                                    ) VALUES (
                                        TG_TABLE_NAME,
                                        NEW.id::text,
                                        col_name,
                                        old_val,
                                        new_val,
                                        current_user
                                    );
                                END IF;
                            END LOOP;
                        END IF;
                        RETURN NEW;
                    END;
                    $$ LANGUAGE plpgsql;
                """)

                # Create triggers for each table
                for table in ['employees', 'app_users', 'applications']:
                    try:
                        # Drop existing trigger if it exists
                        cur.execute(f"DROP TRIGGER IF EXISTS {table}_audit_trigger ON {table};")
                        
                        # Create new trigger
                        cur.execute(f"""
                            CREATE TRIGGER {table}_audit_trigger
                            AFTER UPDATE ON {table}
                            FOR EACH ROW
                            EXECUTE FUNCTION log_data_changes();
                        """)
                    except psycopg2.Error as e:
                        logger.warning(f"Error creating trigger for table {table}: {str(e)}")
                        continue
                
                self.conn.commit()
            except psycopg2.Error as e:
                logger.error(f"Error creating triggers: {str(e)}")
                self.conn.rollback()
                # Don't raise the error, just log it and continue
                pass

    def generate_run_name(self, recon_type, hr_data_version, app_names, timestamp=None):
        """Generate a descriptive run name following the naming convention using epoch time in DDMMYYYY format."""
        if timestamp is None:
            timestamp = datetime.now().strftime('%H%Mhrs')
        
        # Convert epoch time to DDMMYYYY format
        epoch_time = int(datetime.now().timestamp())
        date_str = datetime.fromtimestamp(epoch_time).strftime('%d%m%Y')
        app_str = '_'.join(app_names) if isinstance(app_names, list) else app_names
        
        return f"{recon_type}_HR_{date_str}_{app_str}_Recon_{timestamp}"

    def generate_process_id(self, hr_file, tool_file):
        """Generate a descriptive process ID using epoch time in DDMMYYYY format."""
        epoch_time = int(datetime.now().timestamp())
        date_str = datetime.fromtimestamp(epoch_time).strftime('%d%m%Y')
        hr_name = os.path.splitext(os.path.basename(hr_file))[0][:5]
        tool_name = os.path.splitext(os.path.basename(tool_file))[0][:5]
        return f"REC-{date_str}-{hr_name}-{tool_name}"

    def create_reconciliation_run(self, recon_type, hr_data_source, panel_data_sources, 
                                initiated_by_user_id, description=None):
        """Create a new reconciliation run with enhanced tracking."""
        run_name = self.generate_run_name(
            recon_type=recon_type,
            hr_data_version=hr_data_source,
            app_names=panel_data_sources
        )
        
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO reconciliation_runs 
                (run_name, description, reconciliation_type, hr_data_source, 
                panel_data_sources, start_time, status, initiated_by_user_id)
                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, 'IN_PROGRESS', %s)
                RETURNING id
            """, (run_name, description, recon_type, hr_data_source, 
                  panel_data_sources, initiated_by_user_id))
            return cur.fetchone()[0]

    def update_reconciliation_run_status(self, run_id, status, end_time=None):
        """Update the status and end time of a reconciliation run."""
        with self.conn.cursor() as cur:
            if end_time:
                cur.execute("""
                    UPDATE reconciliation_runs 
                    SET status = %s, end_time = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (status, end_time, run_id))
            else:
                cur.execute("""
                    UPDATE reconciliation_runs 
                    SET status = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (status, run_id))

    def store_reconciliation_results(self, run_id, results):
        """Store detailed reconciliation results with enhanced tracking."""
        with self.conn.cursor() as cur:
            for result in results:
                cur.execute("""
                    INSERT INTO reconciliation_results 
                    (reconciliation_run_id, employee_id, application_id, 
                    hr_status, app_status, reconciliation_status, 
                    recommended_action, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    run_id,
                    result['employee_id'],
                    result['application_id'],
                    result['hr_status'],
                    result['app_status'],
                    result['reconciliation_status'],
                    result['recommended_action'],
                    result.get('notes')
                ))

    def get_active_tools_for_user(self, user_email, filters=None):
        """Get active tools/applications for a specific user with filters."""
        query = """
            SELECT 
                a.name as application_name,
                au.role_name,
                au.status as app_status,
                au.service_id,
                au.h_id,
                au.updated_at as last_updated
            FROM app_users au
            JOIN applications a ON au.application_id = a.id
            JOIN employees e ON au.employee_id = e.id
            WHERE e.email = %s
        """
        params = [user_email]

        if filters:
            if filters.get('status'):
                query += " AND au.status = %s"
                params.append(filters['status'])
            if filters.get('application'):
                query += " AND a.name = %s"
                params.append(filters['application'])
            if filters.get('role'):
                query += " AND au.role_name = %s"
                params.append(filters['role'])

        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchall()

    def get_reconciliation_history(self, filters=None):
        """Get detailed reconciliation history with filters."""
        query = """
            SELECT 
                r.id as run_id,
                r.run_name,
                r.reconciliation_type,
                r.hr_data_source,
                r.panel_data_sources,
                r.start_time,
                r.end_time,
                r.status,
                r.initiated_by_user_id,
                COUNT(rr.id) as total_records,
                COUNT(CASE WHEN rr.reconciliation_status != 'MATCH' THEN 1 END) as discrepancies
            FROM reconciliation_runs r
            LEFT JOIN reconciliation_results rr ON r.id = rr.reconciliation_run_id
            WHERE 1=1
        """
        params = []

        if filters:
            if filters.get('start_date'):
                query += " AND r.start_time >= %s"
                params.append(filters['start_date'])
            if filters.get('end_date'):
                query += " AND r.start_time <= %s"
                params.append(filters['end_date'])
            if filters.get('status'):
                query += " AND r.status = %s"
                params.append(filters['status'])
            if filters.get('reconciliation_type'):
                query += " AND r.reconciliation_type = %s"
                params.append(filters['reconciliation_type'])
            if filters.get('initiated_by'):
                query += " AND r.initiated_by_user_id = %s"
                params.append(filters['initiated_by'])

        query += " GROUP BY r.id ORDER BY r.start_time DESC"

        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchall()

    def log_audit_trail(self, table_name, record_id, action, old_values, new_values, changed_by):
        """Log changes to the audit_log table."""
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO audit_log 
                (table_name, record_id, action, old_values, new_values, changed_by)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (table_name, record_id, action, old_values, new_values, changed_by))

    def get_user_tool_access(self, user_email, include_reconciliation_status=False):
        """Get detailed tool access information for a specific user."""
        query = """
            SELECT 
                e.email,
                e.employment_status as hr_status,
                a.name as app_name,
                au.role_name,
                au.status as app_status,
                au.service_id,
                au.h_id,
                au.last_access,
                au.updated_at as last_updated
        """
        
        if include_reconciliation_status:
            query += """,
                rr.reconciliation_status,
                rr.recommended_action,
                r.run_name as last_reconciliation_run
            """
        
        query += """
            FROM employees e
            JOIN app_users au ON e.id = au.employee_id
            JOIN applications a ON au.application_id = a.id
        """
        
        if include_reconciliation_status:
            query += """
                LEFT JOIN LATERAL (
                    SELECT 
                        rr.reconciliation_status,
                        rr.recommended_action,
                        r.run_name
                    FROM reconciliation_results rr
                    JOIN reconciliation_runs r ON rr.reconciliation_run_id = r.id
                    WHERE rr.employee_id = e.id
                    AND rr.application_id = a.id
                    ORDER BY r.start_time DESC
                    LIMIT 1
                ) rr ON true
            """
        
        query += """
            WHERE e.email = %s
            ORDER BY a.name
        """
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (user_email,))
            return cur.fetchall()

    def get_inactive_users_with_active_tools(self):
        """Get list of inactive employees with active tool access."""
        query = """
            SELECT 
                e.email,
                e.first_name,
                e.last_name,
                e.department,
                e.employment_status,
                a.name as app_name,
                au.role_name,
                au.status as app_status,
                au.service_id,
                au.h_id,
                au.last_access,
                au.updated_at as last_updated
            FROM employees e
            JOIN app_users au ON e.id = au.employee_id
            JOIN applications a ON au.application_id = a.id
            WHERE e.employment_status = 'Inactive'
            AND au.status = 'Active'
            ORDER BY e.email, a.name
        """
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query)
            return cur.fetchall()

    def create_data_snapshot(self, snapshot_type, source_name, data, created_by):
        """Create a snapshot of data for reconciliation runs."""
        version = datetime.now().strftime('%Y%m%d_%H%M%S')
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO data_snapshots 
                (snapshot_type, source_name, version, data, created_by)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (snapshot_type, source_name, version, json.dumps(data), created_by))
            return cur.fetchone()[0]

    def get_data_snapshot(self, snapshot_type, version):
        """Retrieve a specific data snapshot."""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM data_snapshots
                WHERE snapshot_type = %s AND version = %s
            """, (snapshot_type, version))
            return cur.fetchone()

    def get_data_change_history(self, table_name, record_id, start_date=None, end_date=None):
        """Get detailed history of changes for a specific record."""
        query = """
            SELECT 
                field_name,
                old_value,
                new_value,
                changed_by,
                change_timestamp,
                change_reason,
                reconciliation_run_id
            FROM data_change_logs
            WHERE table_name = %s AND record_id = %s
        """
        params = [table_name, record_id]

        if start_date:
            query += " AND change_timestamp >= %s"
            params.append(start_date)
        if end_date:
            query += " AND change_timestamp <= %s"
            params.append(end_date)

        query += " ORDER BY change_timestamp DESC"

        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return cur.fetchall()

    def _verify_table_structure(self):
        """Verify that all required tables exist and have the correct structure."""
        required_tables = [
            'applications',
            'employees',
            'app_users',
            'data_snapshots',
            'reconciliation_runs',
            'reconciliation_results',
            'data_change_logs'
        ]
        
        with self.conn.cursor() as cur:
            for table in required_tables:
                # Check if table exists
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = %s
                    );
                """, (table,))
                exists = cur.fetchone()[0]
                
                if not exists:
                    logger.error(f"Table {table} does not exist!")
                    raise Exception(f"Required table {table} is missing!")
                
                # Get table structure
                cur.execute("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = %s
                    ORDER BY ordinal_position;
                """, (table,))
                columns = cur.fetchall()
                
                logger.info(f"Table {table} structure:")
                for col in columns:
                    logger.info(f"  {col[0]}: {col[1]} ({'NULL' if col[2] == 'YES' else 'NOT NULL'})")

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close() 