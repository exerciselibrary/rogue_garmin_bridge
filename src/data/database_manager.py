#!/usr/bin/env python3
"""
Enhanced Database Manager with Error Handling and Recovery

This module provides robust database operations with:
- Transaction rollback mechanisms for failures
- Database corruption detection and repair procedures
- Automatic backup and recovery systems
- Data export capabilities for manual recovery
"""

import sqlite3
import os
import shutil
import json
import csv
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from pathlib import Path
import threading
import time
import hashlib
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.utils.logging_config import get_component_logger

logger = get_component_logger('database')

class DatabaseHealth(Enum):
    """Database health status"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CORRUPTED = "corrupted"
    INACCESSIBLE = "inaccessible"

class BackupType(Enum):
    """Types of database backups"""
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    RECOVERY = "recovery"
    EXPORT = "export"

@dataclass
class DatabaseError:
    """Represents a database error with recovery information"""
    timestamp: datetime
    error_type: str
    error_message: str
    operation: str
    table_name: Optional[str]
    is_recoverable: bool
    recovery_attempted: bool = False
    recovery_successful: bool = False

@dataclass
class BackupInfo:
    """Information about a database backup"""
    filename: str
    filepath: str
    timestamp: datetime
    backup_type: BackupType
    size_bytes: int
    checksum: str
    is_valid: bool = True

class DatabaseManager:
    """
    Enhanced database manager with comprehensive error handling and recovery
    """
    
    def __init__(self, db_path: str, backup_dir: str = None, 
                 auto_backup_interval: int = 3600):  # 1 hour default
        """
        Initialize the database manager.
        
        Args:
            db_path: Path to the SQLite database file
            backup_dir: Directory for storing backups (default: db_path + '_backups')
            auto_backup_interval: Automatic backup interval in seconds
        """
        self.db_path = os.path.abspath(db_path)
        self.backup_dir = backup_dir or (self.db_path + '_backups')
        self.auto_backup_interval = auto_backup_interval
        
        # Ensure directories exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Error tracking
        self.errors: List[DatabaseError] = []
        self.health_status = DatabaseHealth.HEALTHY
        self.last_health_check: Optional[datetime] = None
        
        # Backup tracking
        self.backups: List[BackupInfo] = []
        self.last_backup: Optional[datetime] = None
        
        # Connection management
        self._connection_lock = threading.RLock()
        self._connection_pool: Dict[int, sqlite3.Connection] = {}
        
        # Statistics
        self.stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'transactions_rolled_back': 0,
            'corruptions_detected': 0,
            'recoveries_attempted': 0,
            'recoveries_successful': 0
        }
        
        # Initialize database
        self._initialize_database()
        
        # Start automatic backup thread
        self._start_backup_thread()
        
        logger.info(f"Database manager initialized: {self.db_path}")
    
    def _initialize_database(self):
        """Initialize the database with proper settings and health check"""
        try:
            # Check if database exists and is accessible
            if os.path.exists(self.db_path):
                health = self._check_database_health()
                if health != DatabaseHealth.HEALTHY:
                    logger.warning(f"Database health check failed: {health.value}")
                    if health == DatabaseHealth.CORRUPTED:
                        self._attempt_database_recovery()
            
            # Create initial connection to ensure database is working
            with self._get_connection() as conn:
                # Enable WAL mode for better concurrency
                conn.execute("PRAGMA journal_mode=WAL")
                # Enable foreign key constraints
                conn.execute("PRAGMA foreign_keys=ON")
                # Set reasonable timeout
                conn.execute("PRAGMA busy_timeout=30000")  # 30 seconds
                
                # Create system tables if they don't exist
                self._create_system_tables(conn)
                
                conn.commit()
            
            logger.info("Database initialized successfully")
            
        except Exception as e:
            error = DatabaseError(
                timestamp=datetime.now(),
                error_type="initialization_error",
                error_message=str(e),
                operation="initialize_database",
                table_name=None,
                is_recoverable=True
            )
            self._handle_database_error(error)
    
    def _create_system_tables(self, conn: sqlite3.Connection):
        """Create system tables for tracking database health and operations"""
        
        # Database health log table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS db_health_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                health_status TEXT NOT NULL,
                details TEXT,
                checksum TEXT
            )
        """)
        
        # Error log table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS db_error_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                error_type TEXT NOT NULL,
                error_message TEXT NOT NULL,
                operation TEXT NOT NULL,
                table_name TEXT,
                is_recoverable INTEGER NOT NULL,
                recovery_attempted INTEGER DEFAULT 0,
                recovery_successful INTEGER DEFAULT 0
            )
        """)
        
        # Backup log table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS db_backup_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                filepath TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                backup_type TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                checksum TEXT NOT NULL,
                is_valid INTEGER DEFAULT 1
            )
        """)
    
    @contextmanager
    def _get_connection(self):
        """Get a database connection with proper error handling"""
        thread_id = threading.get_ident()
        
        with self._connection_lock:
            try:
                # Reuse connection for the same thread
                if thread_id in self._connection_pool:
                    conn = self._connection_pool[thread_id]
                    # Test if connection is still valid
                    try:
                        conn.execute("SELECT 1")
                        yield conn
                        return
                    except sqlite3.Error:
                        # Connection is stale, remove it
                        del self._connection_pool[thread_id]
                
                # Create new connection
                conn = sqlite3.connect(
                    self.db_path,
                    timeout=30.0,
                    check_same_thread=False
                )
                conn.row_factory = sqlite3.Row
                
                # Configure connection
                conn.execute("PRAGMA foreign_keys=ON")
                conn.execute("PRAGMA busy_timeout=30000")
                
                self._connection_pool[thread_id] = conn
                yield conn
                
            except sqlite3.Error as e:
                error = DatabaseError(
                    timestamp=datetime.now(),
                    error_type="connection_error",
                    error_message=str(e),
                    operation="get_connection",
                    table_name=None,
                    is_recoverable=True
                )
                self._handle_database_error(error)
                raise
    
    def execute_with_retry(self, operation: str, query: str, params: Tuple = None, 
                          max_retries: int = 3) -> Any:
        """
        Execute a database operation with automatic retry and error handling.
        
        Args:
            operation: Description of the operation
            query: SQL query to execute
            params: Query parameters
            max_retries: Maximum number of retry attempts
            
        Returns:
            Query result
        """
        self.stats['total_operations'] += 1
        
        for attempt in range(max_retries + 1):
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    
                    if params:
                        result = cursor.execute(query, params)
                    else:
                        result = cursor.execute(query)
                    
                    conn.commit()
                    self.stats['successful_operations'] += 1
                    
                    return result
                    
            except sqlite3.IntegrityError as e:
                error = DatabaseError(
                    timestamp=datetime.now(),
                    error_type="integrity_error",
                    error_message=str(e),
                    operation=operation,
                    table_name=self._extract_table_name(query),
                    is_recoverable=False
                )
                self._handle_database_error(error)
                raise
                
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower() and attempt < max_retries:
                    # Database is locked, wait and retry
                    wait_time = (attempt + 1) * 0.1  # Exponential backoff
                    logger.warning(f"Database locked, retrying in {wait_time}s (attempt {attempt + 1})")
                    time.sleep(wait_time)
                    continue
                elif "database disk image is malformed" in str(e).lower():
                    # Database corruption detected
                    error = DatabaseError(
                        timestamp=datetime.now(),
                        error_type="corruption_error",
                        error_message=str(e),
                        operation=operation,
                        table_name=self._extract_table_name(query),
                        is_recoverable=True
                    )
                    self._handle_database_error(error)
                    self._attempt_database_recovery()
                    raise
                else:
                    error = DatabaseError(
                        timestamp=datetime.now(),
                        error_type="operational_error",
                        error_message=str(e),
                        operation=operation,
                        table_name=self._extract_table_name(query),
                        is_recoverable=attempt < max_retries
                    )
                    self._handle_database_error(error)
                    if attempt >= max_retries:
                        raise
                    
            except Exception as e:
                error = DatabaseError(
                    timestamp=datetime.now(),
                    error_type="unknown_error",
                    error_message=str(e),
                    operation=operation,
                    table_name=self._extract_table_name(query),
                    is_recoverable=attempt < max_retries
                )
                self._handle_database_error(error)
                if attempt >= max_retries:
                    raise
        
        self.stats['failed_operations'] += 1
        raise Exception(f"Operation failed after {max_retries + 1} attempts")
    
    @contextmanager
    def transaction(self):
        """
        Context manager for database transactions with automatic rollback on error.
        """
        with self._get_connection() as conn:
            try:
                conn.execute("BEGIN TRANSACTION")
                yield conn
                conn.commit()
                logger.debug("Transaction committed successfully")
                
            except Exception as e:
                conn.rollback()
                self.stats['transactions_rolled_back'] += 1
                
                error = DatabaseError(
                    timestamp=datetime.now(),
                    error_type="transaction_error",
                    error_message=str(e),
                    operation="transaction",
                    table_name=None,
                    is_recoverable=True
                )
                self._handle_database_error(error)
                
                logger.error(f"Transaction rolled back due to error: {e}")
                raise
    
    def _extract_table_name(self, query: str) -> Optional[str]:
        """Extract table name from SQL query for error reporting"""
        try:
            query_upper = query.upper().strip()
            
            # Handle different SQL operations
            if query_upper.startswith('INSERT INTO'):
                parts = query_upper.split()
                return parts[2] if len(parts) > 2 else None
            elif query_upper.startswith('UPDATE'):
                parts = query_upper.split()
                return parts[1] if len(parts) > 1 else None
            elif query_upper.startswith('DELETE FROM'):
                parts = query_upper.split()
                return parts[2] if len(parts) > 2 else None
            elif query_upper.startswith('SELECT'):
                # Extract from FROM clause
                from_index = query_upper.find('FROM')
                if from_index != -1:
                    parts = query_upper[from_index:].split()
                    return parts[1] if len(parts) > 1 else None
            
            return None
        except Exception:
            return None
    
    def _handle_database_error(self, error: DatabaseError):
        """Handle database errors with logging and recovery attempts"""
        self.errors.append(error)
        
        # Keep only the last 100 errors to prevent memory issues
        if len(self.errors) > 100:
            self.errors = self.errors[-100:]
        
        # Log the error
        logger.error(f"Database error in {error.operation}: {error.error_message}")
        
        # Update health status
        if error.error_type == "corruption_error":
            self.health_status = DatabaseHealth.CORRUPTED
            self.stats['corruptions_detected'] += 1
        elif error.error_type in ["connection_error", "operational_error"]:
            if self.health_status == DatabaseHealth.HEALTHY:
                self.health_status = DatabaseHealth.WARNING
        
        # Log error to database (if possible)
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO db_error_log 
                    (timestamp, error_type, error_message, operation, table_name, is_recoverable)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    error.timestamp.isoformat(),
                    error.error_type,
                    error.error_message,
                    error.operation,
                    error.table_name,
                    1 if error.is_recoverable else 0
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to log error to database: {e}")
    
    def _check_database_health(self) -> DatabaseHealth:
        """
        Perform comprehensive database health check.
        
        Returns:
            DatabaseHealth status
        """
        try:
            with self._get_connection() as conn:
                # Check database integrity
                cursor = conn.execute("PRAGMA integrity_check")
                integrity_result = cursor.fetchone()
                
                if integrity_result and integrity_result[0] != "ok":
                    logger.error(f"Database integrity check failed: {integrity_result[0]}")
                    return DatabaseHealth.CORRUPTED
                
                # Check if we can perform basic operations
                conn.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1")
                
                # Update last health check time
                self.last_health_check = datetime.now()
                
                # Log health check
                conn.execute("""
                    INSERT INTO db_health_log (timestamp, health_status, details)
                    VALUES (?, ?, ?)
                """, (
                    self.last_health_check.isoformat(),
                    "healthy",
                    "Routine health check passed"
                ))
                conn.commit()
                
                return DatabaseHealth.HEALTHY
                
        except sqlite3.DatabaseError as e:
            if "database disk image is malformed" in str(e).lower():
                logger.error("Database corruption detected during health check")
                return DatabaseHealth.CORRUPTED
            else:
                logger.error(f"Database health check failed: {e}")
                return DatabaseHealth.WARNING
                
        except Exception as e:
            logger.error(f"Database health check error: {e}")
            return DatabaseHealth.INACCESSIBLE
    
    def _attempt_database_recovery(self) -> bool:
        """
        Attempt to recover a corrupted database.
        
        Returns:
            True if recovery successful, False otherwise
        """
        logger.info("Attempting database recovery...")
        self.stats['recoveries_attempted'] += 1
        
        try:
            # Create a backup of the corrupted database
            corrupted_backup = self.create_backup(BackupType.RECOVERY)
            
            # Try to recover using SQLite's dump and restore
            recovery_path = self.db_path + ".recovery"
            
            # Dump the database to SQL
            with sqlite3.connect(self.db_path) as source_conn:
                with open(recovery_path + ".sql", 'w') as f:
                    for line in source_conn.iterdump():
                        f.write('%s\n' % line)
            
            # Create new database from the dump
            with sqlite3.connect(recovery_path) as new_conn:
                with open(recovery_path + ".sql", 'r') as f:
                    new_conn.executescript(f.read())
            
            # Verify the recovered database
            with sqlite3.connect(recovery_path) as test_conn:
                cursor = test_conn.execute("PRAGMA integrity_check")
                integrity_result = cursor.fetchone()
                
                if integrity_result and integrity_result[0] == "ok":
                    # Recovery successful, replace the original
                    shutil.move(recovery_path, self.db_path)
                    
                    # Clean up
                    os.remove(recovery_path + ".sql")
                    
                    self.health_status = DatabaseHealth.HEALTHY
                    self.stats['recoveries_successful'] += 1
                    
                    logger.info("Database recovery successful")
                    return True
                else:
                    logger.error("Recovered database failed integrity check")
                    return False
                    
        except Exception as e:
            logger.error(f"Database recovery failed: {e}")
            return False
        finally:
            # Clean up temporary files
            for temp_file in [recovery_path, recovery_path + ".sql"]:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception:
                        pass
        
        return False
    
    def create_backup(self, backup_type: BackupType = BackupType.MANUAL) -> BackupInfo:
        """
        Create a database backup.
        
        Args:
            backup_type: Type of backup to create
            
        Returns:
            BackupInfo object with backup details
        """
        timestamp = datetime.now()
        filename = f"backup_{timestamp.strftime('%Y%m%d_%H%M%S')}_{backup_type.value}.db"
        filepath = os.path.join(self.backup_dir, filename)
        
        try:
            # Create backup using SQLite's backup API
            with sqlite3.connect(self.db_path) as source:
                with sqlite3.connect(filepath) as backup:
                    source.backup(backup)
            
            # Calculate file size and checksum
            size_bytes = os.path.getsize(filepath)
            checksum = self._calculate_file_checksum(filepath)
            
            # Create backup info
            backup_info = BackupInfo(
                filename=filename,
                filepath=filepath,
                timestamp=timestamp,
                backup_type=backup_type,
                size_bytes=size_bytes,
                checksum=checksum
            )
            
            # Verify backup integrity
            backup_info.is_valid = self._verify_backup(filepath)
            
            # Log backup to database
            try:
                with self._get_connection() as conn:
                    conn.execute("""
                        INSERT INTO db_backup_log 
                        (filename, filepath, timestamp, backup_type, size_bytes, checksum, is_valid)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        filename, filepath, timestamp.isoformat(), backup_type.value,
                        size_bytes, checksum, 1 if backup_info.is_valid else 0
                    ))
                    conn.commit()
            except Exception as e:
                logger.error(f"Failed to log backup to database: {e}")
            
            self.backups.append(backup_info)
            self.last_backup = timestamp
            
            logger.info(f"Backup created: {filename} ({size_bytes} bytes)")
            return backup_info
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise
    
    def _calculate_file_checksum(self, filepath: str) -> str:
        """Calculate SHA-256 checksum of a file"""
        hash_sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def _verify_backup(self, backup_path: str) -> bool:
        """Verify backup integrity"""
        try:
            with sqlite3.connect(backup_path) as conn:
                cursor = conn.execute("PRAGMA integrity_check")
                result = cursor.fetchone()
                return result and result[0] == "ok"
        except Exception as e:
            logger.error(f"Backup verification failed: {e}")
            return False
    
    def restore_from_backup(self, backup_info: BackupInfo) -> bool:
        """
        Restore database from a backup.
        
        Args:
            backup_info: Backup to restore from
            
        Returns:
            True if restore successful, False otherwise
        """
        logger.info(f"Restoring database from backup: {backup_info.filename}")
        
        try:
            # Verify backup before restore
            if not self._verify_backup(backup_info.filepath):
                logger.error("Backup verification failed, cannot restore")
                return False
            
            # Create a backup of current database before restore
            current_backup = self.create_backup(BackupType.RECOVERY)
            
            # Close all connections
            with self._connection_lock:
                for conn in self._connection_pool.values():
                    conn.close()
                self._connection_pool.clear()
            
            # Replace current database with backup
            shutil.copy2(backup_info.filepath, self.db_path)
            
            # Verify restored database
            health = self._check_database_health()
            if health == DatabaseHealth.HEALTHY:
                logger.info("Database restore successful")
                return True
            else:
                logger.error("Restored database failed health check")
                # Restore the previous database
                shutil.copy2(current_backup.filepath, self.db_path)
                return False
                
        except Exception as e:
            logger.error(f"Database restore failed: {e}")
            return False
    
    def export_data(self, export_format: str = "json", 
                   tables: List[str] = None) -> str:
        """
        Export database data for manual recovery.
        
        Args:
            export_format: Format to export ("json", "csv", "sql")
            tables: List of tables to export (None for all)
            
        Returns:
            Path to exported file
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        export_filename = f"export_{timestamp}.{export_format}"
        export_path = os.path.join(self.backup_dir, export_filename)
        
        try:
            with self._get_connection() as conn:
                if not tables:
                    # Get all table names
                    cursor = conn.execute("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name NOT LIKE 'sqlite_%'
                    """)
                    tables = [row[0] for row in cursor.fetchall()]
                
                if export_format == "json":
                    self._export_to_json(conn, tables, export_path)
                elif export_format == "csv":
                    self._export_to_csv(conn, tables, export_path)
                elif export_format == "sql":
                    self._export_to_sql(conn, tables, export_path)
                else:
                    raise ValueError(f"Unsupported export format: {export_format}")
            
            logger.info(f"Data exported to: {export_path}")
            return export_path
            
        except Exception as e:
            logger.error(f"Data export failed: {e}")
            raise
    
    def _export_to_json(self, conn: sqlite3.Connection, tables: List[str], export_path: str):
        """Export data to JSON format"""
        export_data = {}
        
        for table in tables:
            cursor = conn.execute(f"SELECT * FROM {table}")
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            
            export_data[table] = {
                "columns": columns,
                "data": [dict(zip(columns, row)) for row in rows]
            }
        
        with open(export_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
    
    def _export_to_csv(self, conn: sqlite3.Connection, tables: List[str], export_path: str):
        """Export data to CSV format (creates separate files for each table)"""
        base_path = export_path.replace('.csv', '')
        
        for table in tables:
            table_path = f"{base_path}_{table}.csv"
            cursor = conn.execute(f"SELECT * FROM {table}")
            
            with open(table_path, 'w', newline='') as f:
                writer = csv.writer(f)
                # Write header
                writer.writerow([description[0] for description in cursor.description])
                # Write data
                writer.writerows(cursor.fetchall())
    
    def _export_to_sql(self, conn: sqlite3.Connection, tables: List[str], export_path: str):
        """Export data to SQL format"""
        with open(export_path, 'w') as f:
            for table in tables:
                # Write table schema
                cursor = conn.execute(f"SELECT sql FROM sqlite_master WHERE name='{table}'")
                schema = cursor.fetchone()
                if schema:
                    f.write(f"{schema[0]};\n\n")
                
                # Write table data
                cursor = conn.execute(f"SELECT * FROM {table}")
                columns = [description[0] for description in cursor.description]
                
                for row in cursor.fetchall():
                    values = []
                    for value in row:
                        if value is None:
                            values.append("NULL")
                        elif isinstance(value, str):
                            values.append(f"'{value.replace(\"'\", \"''\")}'")
                        else:
                            values.append(str(value))
                    
                    f.write(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(values)});\n")
                
                f.write("\n")
    
    def _start_backup_thread(self):
        """Start automatic backup thread"""
        def backup_worker():
            while True:
                try:
                    time.sleep(self.auto_backup_interval)
                    
                    # Only create automatic backup if database is healthy
                    if self.health_status == DatabaseHealth.HEALTHY:
                        self.create_backup(BackupType.AUTOMATIC)
                        
                        # Clean up old automatic backups (keep last 10)
                        self._cleanup_old_backups()
                    
                except Exception as e:
                    logger.error(f"Automatic backup failed: {e}")
        
        backup_thread = threading.Thread(target=backup_worker, daemon=True)
        backup_thread.start()
        logger.info(f"Automatic backup thread started (interval: {self.auto_backup_interval}s)")
    
    def _cleanup_old_backups(self, keep_count: int = 10):
        """Clean up old automatic backups"""
        try:
            # Get all automatic backups sorted by timestamp
            auto_backups = [b for b in self.backups if b.backup_type == BackupType.AUTOMATIC]
            auto_backups.sort(key=lambda x: x.timestamp, reverse=True)
            
            # Remove old backups
            for backup in auto_backups[keep_count:]:
                if os.path.exists(backup.filepath):
                    os.remove(backup.filepath)
                    logger.debug(f"Removed old backup: {backup.filename}")
                
                self.backups.remove(backup)
                
        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}")
    
    def get_database_status(self) -> Dict[str, Any]:
        """
        Get comprehensive database status information.
        
        Returns:
            Dictionary with database status and metrics
        """
        # Perform health check if it's been a while
        if (not self.last_health_check or 
            datetime.now() - self.last_health_check > timedelta(minutes=5)):
            self.health_status = self._check_database_health()
        
        return {
            "health_status": self.health_status.value,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "database_path": self.db_path,
            "database_size_bytes": os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0,
            "backup_directory": self.backup_dir,
            "last_backup": self.last_backup.isoformat() if self.last_backup else None,
            "backup_count": len(self.backups),
            "statistics": self.stats.copy(),
            "recent_errors": [
                {
                    "timestamp": error.timestamp.isoformat(),
                    "type": error.error_type,
                    "message": error.error_message,
                    "operation": error.operation,
                    "table": error.table_name,
                    "recoverable": error.is_recoverable
                }
                for error in self.errors[-5:]  # Last 5 errors
            ]
        }
    
    def close(self):
        """Close all database connections and cleanup"""
        with self._connection_lock:
            for conn in self._connection_pool.values():
                conn.close()
            self._connection_pool.clear()
        
        logger.info("Database manager closed")