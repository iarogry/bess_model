import os
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

class DBConnector:
    _pool = None

    @classmethod
    def get_pool(cls):
        if cls._pool is None:
            try:
                cls._pool = psycopg2.pool.SimpleConnectionPool(
                    1, 20,
                    dbname=os.getenv("DB_NAME", "battery_sim"),
                    user=os.getenv("DB_USER", "iaroslav"),
                    password=os.getenv("DB_PASS", "vinylfun-1206"),
                    host=os.getenv("DB_HOST", "localhost"),
                    port=os.getenv("DB_PORT", "5432")
                )
                logger.info("PostgreSQL connection pool created successfully")
            except Exception as e:
                logger.error(f"Error creating PostgreSQL connection pool: {e}")
                raise
        return cls._pool

    @classmethod
    def get_connection(cls):
        return cls.get_pool().getconn()

    @classmethod
    def release_connection(cls, conn):
        cls.get_pool().putconn(conn)

def get_db_params():
    """Returns a dict of DB params for direct psycopg2.connect if needed"""
    return {
        "dbname": os.getenv("DB_NAME", "battery_sim"),
        "user": os.getenv("DB_USER", "iaroslav"),
        "password": os.getenv("DB_PASS", "vinylfun-1206"),
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432")
    }
