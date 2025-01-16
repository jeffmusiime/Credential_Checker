#!/usr/bin/env python3
import psycopg2
import redis
import yaml
import argparse
import logging
from typing import Dict, List, Optional
import sys
import mysql.connector
import pymongo
import pymssql
import oracledb

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CredentialChecker:
    def __init__(self, config_path: str):
        """Initialize the credential checker with configuration file path."""
        self.config = self._load_config(config_path)
        self.results = []

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            sys.exit(1)

    def check_postgres(self, host: str, port: int, username: str, password: str) -> bool:
        """Check PostgreSQL connection with given credentials."""
        try:
            conn = psycopg2.connect(
                host=host,
                port=port,
                user=username,
                password=password,
                database="postgres",
                connect_timeout=3
            )
            conn.close()
            return True
        except Exception:
            return False

    def check_mysql(self, host: str, port: int, username: str, password: str) -> bool:
        """Check MySQL/MariaDB connection with given credentials."""
        try:
            conn = mysql.connector.connect(
                host=host,
                port=port,
                user=username,
                password=password,
                connection_timeout=3
            )
            conn.close()
            return True
        except Exception:
            return False

    def check_mongodb(self, host: str, port: int, username: str, password: str) -> bool:
        """Check MongoDB connection with given credentials."""
        try:
            uri = f"mongodb://{username}:{password}@{host}:{port}/?serverSelectionTimeoutMS=3000"
            client = pymongo.MongoClient(uri)
            # Force connection attempt
            client.server_info()
            client.close()
            return True
        except Exception:
            return False

    def check_mssql(self, host: str, port: int, username: str, password: str) -> bool:
        """Check Microsoft SQL Server connection with given credentials."""
        try:
            conn = pymssql.connect(
                server=host,
                port=port,
                user=username,
                password=password,
                login_timeout=3
            )
            conn.close()
            return True
        except Exception:
            return False

    def check_oracle(self, host: str, port: int, username: str, password: str) -> bool:
        """Check Oracle Database connection with given credentials."""
        try:
            dsn = f"{host}:{port}/ORCL"
            conn = oracledb.connect(
                user=username,
                password=password,
                dsn=dsn,
                timeout=3
            )
            conn.close()
            return True
        except Exception:
            return False

    def check_redis(self, host: str, port: int, password: str) -> bool:
        """Check Redis connection with given credentials."""
        try:
            r = redis.Redis(
                host=host,
                port=port,
                password=password,
                socket_timeout=3
            )
            r.ping()
            return True
        except Exception:
            return False

    def check_database(self, db_type: str, config: Dict, cred: Dict) -> None:
        """Generic database checking method."""
        check_methods = {
            'postgresql': self.check_postgres,
            'mysql': self.check_mysql,
            'mongodb': self.check_mongodb,
            'mssql': self.check_mssql,
            'oracle': self.check_oracle
        }
        
        if db_type not in check_methods:
            logger.error(f"Unsupported database type: {db_type}")
            return

        success = check_methods[db_type](
            config['host'],
            config['port'],
            cred['username'],
            cred['password']
        )
        
        if success:
            self.results.append({
                'service': db_type.upper(),
                'host': config['host'],
                'port': config['port'],
                'username': cred['username'],
                'password': cred['password']
            })
            logger.warning(f"Default {db_type.upper()} credentials found: {cred['username']}:{cred['password']}")

    def run_checks(self):
        """Run credential checks for all configured services."""
        # Check all database services
        database_services = ['postgresql', 'mysql', 'mongodb', 'mssql', 'oracle']
        
        for db_type in database_services:
            if db_type in self.config:
                logger.info(f"Checking {db_type.upper()} credentials...")
                db_config = self.config[db_type]
                
                for cred in db_config['default_credentials']:
                    self.check_database(db_type, db_config, cred)

        # Check Redis
        if 'redis' in self.config:
            redis_config = self.config['redis']
            logger.info("Checking Redis credentials...")
            
            for password in redis_config['default_passwords']:
                success = self.check_redis(
                    redis_config['host'],
                    redis_config['port'],
                    password
                )
                
                if success:
                    self.results.append({
                        'service': 'Redis',
                        'host': redis_config['host'],
                        'port': redis_config['port'],
                        'password': password
                    })
                    logger.warning(f"Default Redis password found: {password}")

        return self.results

def main():
    parser = argparse.ArgumentParser(description='Check for default credentials in various services')
    parser.add_argument('--config', required=True, help='Path to YAML configuration file')
    args = parser.parse_args()

    checker = CredentialChecker(args.config)
    results = checker.run_checks()

    if results:
        logger.warning("Default credentials found!")
        for result in results:
            logger.warning(f"Service: {result['service']}")
            logger.warning(f"Host: {result['host']}:{result['port']}")
            if 'username' in result:
                logger.warning(f"Username: {result['username']}")
            logger.warning(f"Password: {result['password']}")
            logger.warning("-" * 50)
    else:
        logger.info("No default credentials found.")

if __name__ == "__main__":
    main()
