import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, JSON, UniqueConstraint, func
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import uuid
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()
DB_PATH = os.getenv('SQLITE_DB_PATH', 'reconify.db')
DB_URL = f'sqlite:///{DB_PATH}'

# SQLAlchemy models
def generate_uuid():
    return str(uuid.uuid4())

class Application(Base):
    __tablename__ = 'applications'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    app_users = relationship('AppUser', back_populates='application')

class Employee(Base):
    __tablename__ = 'employees'
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    manager_email = Column(String(255))
    department = Column(String(100))
    employee_type = Column(String(50))
    employment_status = Column(String(50), default='Active')
    last_hr_update = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    app_users = relationship('AppUser', back_populates='employee')

class AppUser(Base):
    __tablename__ = 'app_users'
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey('employees.id'))
    application_id = Column(Integer, ForeignKey('applications.id'))
    role_name = Column(String(100))
    status = Column(String(50), default='Active')
    service_id = Column(String(100))
    h_id = Column(String(100))
    last_access = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    employee = relationship('Employee', back_populates='app_users')
    application = relationship('Application', back_populates='app_users')
    __table_args__ = (UniqueConstraint('employee_id', 'application_id', name='_employee_app_uc'),)

class DataSnapshot(Base):
    __tablename__ = 'data_snapshots'
    id = Column(Integer, primary_key=True)
    snapshot_type = Column(String(50), nullable=False)
    source_name = Column(String(255), nullable=False)
    version = Column(String(50), nullable=False)
    data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(255), nullable=False)

class ReconciliationRun(Base):
    __tablename__ = 'reconciliation_runs'
    id = Column(String(36), primary_key=True, default=generate_uuid)
    run_name = Column(String(255), nullable=False)
    description = Column(Text)
    reconciliation_type = Column(String(50), nullable=False)
    hr_data_source = Column(String(255), nullable=False)
    panel_data_sources = Column(Text, nullable=False)  # Store as comma-separated string
    start_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_time = Column(DateTime)
    status = Column(String(50), nullable=False)
    initiated_by_user_id = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    results = relationship('ReconciliationResult', back_populates='run')

class ReconciliationResult(Base):
    __tablename__ = 'reconciliation_results'
    id = Column(Integer, primary_key=True)
    reconciliation_run_id = Column(String(36), ForeignKey('reconciliation_runs.id'))
    employee_id = Column(Integer, ForeignKey('employees.id'))
    application_id = Column(Integer, ForeignKey('applications.id'))
    hr_status = Column(String(50))
    app_status = Column(String(50))
    reconciliation_status = Column(String(100))
    recommended_action = Column(String(100))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    run = relationship('ReconciliationRun', back_populates='results')

class DataChangeLog(Base):
    __tablename__ = 'data_change_logs'
    id = Column(Integer, primary_key=True)
    table_name = Column(String(100), nullable=False)
    record_id = Column(String(100), nullable=False)
    field_name = Column(String(100), nullable=False)
    old_value = Column(Text)
    new_value = Column(Text)
    changed_by = Column(String(255), nullable=False)
    change_timestamp = Column(DateTime, default=datetime.utcnow)
    change_reason = Column(Text)
    reconciliation_run_id = Column(String(36), ForeignKey('reconciliation_runs.id'))

class AuditLog(Base):
    __tablename__ = 'audit_log'
    id = Column(Integer, primary_key=True)
    table_name = Column(String(100), nullable=False)
    record_id = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    old_values = Column(Text)
    new_values = Column(Text)
    changed_by = Column(String(255), nullable=False)
    change_timestamp = Column(DateTime, default=datetime.utcnow)

# Database handler using SQLAlchemy
class DatabaseHandler:
    def __init__(self):
        self.engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        logger.info(f"Connected to SQLite database at {DB_PATH}")

    def _get_session(self):
        return self.Session()

    def _create_tables(self):
        # No-op: tables are created in __init__
        pass

    def _create_triggers(self):
        # SQLite does not support triggers in the same way; skip for now
        pass

    def generate_run_name(self, recon_type, hr_data_version, app_names, timestamp=None):
        if timestamp is None:
            timestamp = datetime.now().strftime('%H%Mhrs')
        epoch_time = int(datetime.now().timestamp())
        date_str = datetime.fromtimestamp(epoch_time).strftime('%d%m%Y')
        app_str = '_'.join(app_names) if isinstance(app_names, list) else app_names
        return f"{recon_type}_HR_{date_str}_{app_str}_Recon_{timestamp}"

    def generate_process_id(self, hr_file, tool_file):
        epoch_time = int(datetime.now().timestamp())
        date_str = datetime.fromtimestamp(epoch_time).strftime('%d%m%Y')
        hr_name = os.path.splitext(os.path.basename(hr_file))[0][:5]
        tool_name = os.path.splitext(os.path.basename(tool_file))[0][:5]
        return f"REC-{date_str}-{hr_name}-{tool_name}"

    def create_reconciliation_run(self, recon_type, hr_data_source, panel_data_sources, initiated_by_user_id, description=None):
        session = self._get_session()
        try:
            run_name = self.generate_run_name(recon_type, hr_data_source, panel_data_sources)
            run = ReconciliationRun(
                run_name=run_name,
                description=description,
                reconciliation_type=recon_type,
                hr_data_source=hr_data_source,
                panel_data_sources=','.join(panel_data_sources) if isinstance(panel_data_sources, list) else str(panel_data_sources),
                status='IN_PROGRESS',
                initiated_by_user_id=initiated_by_user_id
            )
            session.add(run)
            session.commit()
            return run.id
        finally:
            session.close()

    def update_reconciliation_run_status(self, run_id, status, end_time=None):
        session = self._get_session()
        try:
            run = session.query(ReconciliationRun).filter_by(id=run_id).first()
            if run:
                run.status = status
                if end_time:
                    run.end_time = end_time
                run.updated_at = datetime.utcnow()
                session.commit()
        finally:
            session.close()

    def store_reconciliation_results(self, run_id, results):
        session = self._get_session()
        try:
            for result in results:
                rec_result = ReconciliationResult(
                    reconciliation_run_id=run_id,
                    employee_id=result['employee_id'],
                    application_id=result['application_id'],
                    hr_status=result['hr_status'],
                    app_status=result['app_status'],
                    reconciliation_status=result['reconciliation_status'],
                    recommended_action=result['recommended_action'],
                    notes=result.get('notes')
                )
                session.add(rec_result)
            session.commit()
        finally:
            session.close()

    def get_active_tools_for_user(self, user_email, filters=None):
        session = self._get_session()
        try:
            query = session.query(Application.name.label('application_name'),
                                 AppUser.role_name,
                                 AppUser.status.label('app_status'),
                                 AppUser.service_id,
                                 AppUser.h_id,
                                 AppUser.updated_at.label('last_updated')) \
                .join(AppUser, AppUser.application_id == Application.id) \
                .join(Employee, AppUser.employee_id == Employee.id) \
                .filter(Employee.email == user_email)
            if filters:
                if filters.get('status'):
                    query = query.filter(AppUser.status == filters['status'])
                if filters.get('application'):
                    query = query.filter(Application.name == filters['application'])
                if filters.get('role'):
                    query = query.filter(AppUser.role_name == filters['role'])
            return [dict(row._mapping) for row in query.all()]
        finally:
            session.close()

    def get_reconciliation_history(self, filters=None):
        session = self._get_session()
        try:
            query = session.query(
                ReconciliationRun.id.label('run_id'),
                ReconciliationRun.run_name,
                ReconciliationRun.reconciliation_type,
                ReconciliationRun.hr_data_source,
                ReconciliationRun.panel_data_sources,
                ReconciliationRun.start_time,
                ReconciliationRun.end_time,
                ReconciliationRun.status,
                ReconciliationRun.initiated_by_user_id,
                func.count(ReconciliationResult.id).label('total_records'),
                func.count(func.nullif(ReconciliationResult.reconciliation_status == 'MATCH', True)).label('discrepancies')
            ).outerjoin(ReconciliationResult, ReconciliationRun.id == ReconciliationResult.reconciliation_run_id)
            if filters:
                if filters.get('start_date'):
                    query = query.filter(ReconciliationRun.start_time >= filters['start_date'])
                if filters.get('end_date'):
                    query = query.filter(ReconciliationRun.start_time <= filters['end_date'])
                if filters.get('status'):
                    query = query.filter(ReconciliationRun.status == filters['status'])
                if filters.get('reconciliation_type'):
                    query = query.filter(ReconciliationRun.reconciliation_type == filters['reconciliation_type'])
                if filters.get('initiated_by'):
                    query = query.filter(ReconciliationRun.initiated_by_user_id == filters['initiated_by'])
            query = query.group_by(ReconciliationRun.id)
            query = query.order_by(ReconciliationRun.start_time.desc())
            return [dict(row._mapping) for row in query.all()]
        finally:
            session.close()

    def log_audit_trail(self, table_name, record_id, action, old_values, new_values, changed_by):
        session = self._get_session()
        try:
            log = AuditLog(
                table_name=table_name,
                record_id=record_id,
                action=action,
                old_values=json.dumps(old_values) if isinstance(old_values, dict) else str(old_values),
                new_values=json.dumps(new_values) if isinstance(new_values, dict) else str(new_values),
                changed_by=changed_by
            )
            session.add(log)
            session.commit()
        finally:
            session.close()

    def get_user_tool_access(self, user_email, include_reconciliation_status=False):
        session = self._get_session()
        try:
            query = session.query(
                Employee.email,
                Employee.employment_status.label('hr_status'),
                Application.name.label('app_name'),
                AppUser.role_name,
                AppUser.status.label('app_status'),
                AppUser.service_id,
                AppUser.h_id,
                AppUser.last_access,
                AppUser.updated_at.label('last_updated')
            ).join(AppUser, Employee.id == AppUser.employee_id)
            query = query.join(Application, AppUser.application_id == Application.id)
            if include_reconciliation_status:
                # Not implemented: would require more complex joins
                pass
            query = query.filter(Employee.email == user_email).order_by(Application.name)
            return [dict(row._mapping) for row in query.all()]
        finally:
            session.close()

    def get_inactive_users_with_active_tools(self):
        session = self._get_session()
        try:
            query = session.query(
                Employee.email,
                Employee.first_name,
                Employee.last_name,
                Employee.department,
                Employee.employment_status,
                Application.name.label('app_name'),
                AppUser.role_name,
                AppUser.status.label('app_status'),
                AppUser.service_id,
                AppUser.h_id,
                AppUser.last_access,
                AppUser.updated_at.label('last_updated')
            ).join(AppUser, Employee.id == AppUser.employee_id)
            query = query.join(Application, AppUser.application_id == Application.id)
            query = query.filter(Employee.employment_status == 'Inactive', AppUser.status == 'Active')
            query = query.order_by(Employee.email, Application.name)
            return [dict(row._mapping) for row in query.all()]
        finally:
            session.close()

    def create_data_snapshot(self, snapshot_type, source_name, data, created_by):
        session = self._get_session()
        try:
            version = datetime.now().strftime('%Y%m%d_%H%M%S')
            snapshot = DataSnapshot(
                snapshot_type=snapshot_type,
                source_name=source_name,
                version=version,
                data=data,
                created_by=created_by
            )
            session.add(snapshot)
            session.commit()
            return snapshot.id
        finally:
            session.close()

    def get_data_snapshot(self, snapshot_type, version):
        session = self._get_session()
        try:
            snap = session.query(DataSnapshot).filter_by(snapshot_type=snapshot_type, version=version).first()
            return snap
        finally:
            session.close()

    def get_data_change_history(self, table_name, record_id, start_date=None, end_date=None):
        session = self._get_session()
        try:
            query = session.query(
                DataChangeLog.field_name,
                DataChangeLog.old_value,
                DataChangeLog.new_value,
                DataChangeLog.changed_by,
                DataChangeLog.change_timestamp,
                DataChangeLog.change_reason,
                DataChangeLog.reconciliation_run_id
            ).filter_by(table_name=table_name, record_id=record_id)
            if start_date:
                query = query.filter(DataChangeLog.change_timestamp >= start_date)
            if end_date:
                query = query.filter(DataChangeLog.change_timestamp <= end_date)
            query = query.order_by(DataChangeLog.change_timestamp.desc())
            return [dict(row._mapping) for row in query.all()]
        finally:
            session.close()

    def _verify_table_structure(self):
        # No-op for SQLAlchemy/SQLite
        pass

    def close(self):
        # No-op for SQLAlchemy/SQLite
        pass 