"""
Data collection and storage module for Crypto Trader Pro.

This module provides comprehensive cryptocurrency data management including:
- Database management and storage (CryptoDatabaseManager)
- Real-time data collection (RealTimeDataCollector)
- Intelligent scheduling system (DataCollectionScheduler)
- Data integrity validation and optimization

Version: 1.0.0
"""

from .database import CryptoDatabaseManager, validate_database_integrity, optimize_database
from .collector import RealTimeDataCollector, CollectionStatistics
from .scheduler import DataCollectionScheduler, create_and_start_scheduler

__version__ = "1.0.0"
__author__ = "Crypto Trader Pro Team"

__all__ = [
    # Database management
    'CryptoDatabaseManager',
    'validate_database_integrity',
    'optimize_database',

    # Data collection
    'RealTimeDataCollector',
    'CollectionStatistics',

    # Scheduling
    'DataCollectionScheduler',
    'create_and_start_scheduler'
]