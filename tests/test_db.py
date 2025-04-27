"""Unit tests for database operations."""

import pytest
import pandas as pd
from pathlib import Path
import tempfile
import os
import shutil

from alpha_pulse.db import DuckDBManager
from alpha_pulse.types.edgar8k import Item8K_801

@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test.db")
    
    try:
        yield str(db_path)
    finally:
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

@pytest.fixture
def db_manager(temp_db, monkeypatch):
    """Create a DuckDBManager instance with a temporary database."""
    # Override DUCKDB_PATH environment variable
    monkeypatch.setenv('DUCKDB_PATH', temp_db)
    
    manager = DuckDBManager()
    try:
        yield manager
    finally:
        manager.close()

def test_create_8k_tables(db_manager):
    """Test table creation."""
    # Check if table exists
    exists, count = db_manager.check_table_exists_and_has_records("items_8k_801")
    assert exists
    assert count == 0

def test_insert_and_get_8k_items(db_manager):
    """Test inserting and retrieving items."""
    # Create test data
    test_data = pd.DataFrame({
        'cik': ['0001234567'],
        'filing_date': ['2024-01-01'],
        'item_number': ['8.01'],
        'parsed_text': ['Test text'],
        'event_type': ['Other'],
        'sentiment': [0],
        'event_summary': ['Test summary'],
        'key_takeaway': ['Test takeaway'],
        'probable_price_move': [False],
        'price_move_reason': ['No reason'],
        'is_financially_material': [False],
        'is_operational_impact': [False],
        'is_related_to_prior': [False],
        'is_recent_event': [False],
        'unexpected_timing': [False],
        'mentioned_companies': [''],
        'mentioned_tickers': [''],
        'keywords': [''],
        'strategic_signal': [False],
        'priority_shift_detected': [False]
    })
    
    # Insert data
    db_manager.insert_8k_items(test_data)
    
    # Check if data was inserted
    exists, count = db_manager.check_table_exists_and_has_records("items_8k_801")
    assert exists
    assert count == 1
    
    # Retrieve data
    result = db_manager.get_all_8k_items()
    assert len(result) == 1
    assert result.iloc[0]['cik'] == '0001234567'
    assert result.iloc[0]['filing_date'] == '2024-01-01'
    assert result.iloc[0]['item_number'] == '8.01'

def test_get_8k_items_by_cik(db_manager):
    """Test retrieving items by CIK."""
    # Create test data
    test_data = pd.DataFrame({
        'cik': ['0001234567', '0007654321'],
        'filing_date': ['2024-01-01', '2024-01-02'],
        'item_number': ['8.01', '8.01'],
        'parsed_text': ['Test text 1', 'Test text 2'],
        'event_type': ['Other', 'Other'],
        'sentiment': [0, 0],
        'event_summary': ['Test summary 1', 'Test summary 2'],
        'key_takeaway': ['Test takeaway 1', 'Test takeaway 2'],
        'probable_price_move': [False, False],
        'price_move_reason': ['No reason', 'No reason'],
        'is_financially_material': [False, False],
        'is_operational_impact': [False, False],
        'is_related_to_prior': [False, False],
        'is_recent_event': [False, False],
        'unexpected_timing': [False, False],
        'mentioned_companies': ['', ''],
        'mentioned_tickers': ['', ''],
        'keywords': ['', ''],
        'strategic_signal': [False, False],
        'priority_shift_detected': [False, False]
    })
    
    # Insert data
    db_manager.insert_8k_items(test_data)
    
    # Test retrieval by CIK
    result = db_manager.get_8k_items_by_cik('0001234567')
    assert len(result) == 1
    assert result.iloc[0]['cik'] == '0001234567'
    assert result.iloc[0]['filing_date'] == '2024-01-01'

def test_get_8k_items_by_date(db_manager):
    """Test retrieving items by filing date."""
    # Create test data
    test_data = pd.DataFrame({
        'cik': ['0001234567', '0007654321'],
        'filing_date': ['2024-01-01', '2024-01-02'],
        'item_number': ['8.01', '8.01'],
        'parsed_text': ['Test text 1', 'Test text 2'],
        'event_type': ['Other', 'Other'],
        'sentiment': [0, 0],
        'event_summary': ['Test summary 1', 'Test summary 2'],
        'key_takeaway': ['Test takeaway 1', 'Test takeaway 2'],
        'probable_price_move': [False, False],
        'price_move_reason': ['No reason', 'No reason'],
        'is_financially_material': [False, False],
        'is_operational_impact': [False, False],
        'is_related_to_prior': [False, False],
        'is_recent_event': [False, False],
        'unexpected_timing': [False, False],
        'mentioned_companies': ['', ''],
        'mentioned_tickers': ['', ''],
        'keywords': ['', ''],
        'strategic_signal': [False, False],
        'priority_shift_detected': [False, False]
    })
    
    # Insert data
    db_manager.insert_8k_items(test_data)
    
    # Test retrieval by date
    result = db_manager.get_8k_items_by_date('2024-01-01')
    assert len(result) == 1
    assert result.iloc[0]['cik'] == '0001234567'
    assert result.iloc[0]['filing_date'] == '2024-01-01'

def test_get_8k_items_by_event_type(db_manager):
    """Test retrieving items by event type."""
    # Create test data
    test_data = pd.DataFrame({
        'cik': ['0001234567', '0007654321'],
        'filing_date': ['2024-01-01', '2024-01-02'],
        'item_number': ['8.01', '8.01'],
        'parsed_text': ['Test text 1', 'Test text 2'],
        'event_type': ['M&A', 'Other'],
        'sentiment': [0, 0],
        'event_summary': ['Test summary 1', 'Test summary 2'],
        'key_takeaway': ['Test takeaway 1', 'Test takeaway 2'],
        'probable_price_move': [False, False],
        'price_move_reason': ['No reason', 'No reason'],
        'is_financially_material': [False, False],
        'is_operational_impact': [False, False],
        'is_related_to_prior': [False, False],
        'is_recent_event': [False, False],
        'unexpected_timing': [False, False],
        'mentioned_companies': ['', ''],
        'mentioned_tickers': ['', ''],
        'keywords': ['', ''],
        'strategic_signal': [False, False],
        'priority_shift_detected': [False, False]
    })
    
    # Insert data
    db_manager.insert_8k_items(test_data)
    
    # Test retrieval by event type
    result = db_manager.get_8k_items_by_event_type('M&A')
    assert len(result) == 1
    assert result.iloc[0]['cik'] == '0001234567'
    assert result.iloc[0]['event_type'] == 'M&A'

def test_get_all_filings(db_manager):
    """Test retrieving all filings."""
    # Create test data
    test_data = pd.DataFrame({
        'cik': ['0001234567', '0007654321'],
        'filing_date': ['2024-01-01', '2024-01-02'],
        'item_number': ['8.01', '8.01'],
        'parsed_text': ['Test text 1', 'Test text 2'],
        'event_type': ['M&A', 'Other'],
        'sentiment': [0, 0],
        'event_summary': ['Test summary 1', 'Test summary 2'],
        'key_takeaway': ['Test takeaway 1', 'Test takeaway 2'],
        'probable_price_move': [False, False],
        'price_move_reason': ['No reason', 'No reason'],
        'is_financially_material': [False, False],
        'is_operational_impact': [False, False],
        'is_related_to_prior': [False, False],
        'is_recent_event': [False, False],
        'unexpected_timing': [False, False],
        'mentioned_companies': ['', ''],
        'mentioned_tickers': ['', ''],
        'keywords': ['', ''],
        'strategic_signal': [False, False],
        'priority_shift_detected': [False, False]
    })
    
    # Insert data
    db_manager.insert_8k_items(test_data)
    
    # Test retrieval of all filings
    result = db_manager.get_all_filings()
    assert len(result) == 2
    assert set(result['cik']) == {'0001234567', '0007654321'}
    assert set(result['filing_date']) == {'2024-01-01', '2024-01-02'}
    assert set(result['event_type']) == {'M&A', 'Other'}

def test_invalid_insert(db_manager):
    """Test inserting invalid data."""
    with pytest.raises(ValueError):
        db_manager.insert_8k_items("invalid_data") 