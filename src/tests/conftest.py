import pytest
import os
import logging

import pandas as pd
from reportportal_client import RPLogger


@pytest.fixture
def test_csv_path():
    test_path = 'test.csv'
    yield test_path
    if os.path.exists(test_path):
        os.remove(test_path)


@pytest.fixture
def test_avro_path():
    test_path = 'test.avro'
    yield test_path
    if os.path.exists(test_path):
        os.remove(test_path)


@pytest.fixture
def test_pickle_path():
    test_path = 'test.pkl'
    yield test_path
    if os.path.exists(test_path):
        os.remove(test_path)


@pytest.fixture
def test_pickle_path():
    test_path = 'test.pkl'
    yield test_path
    if os.path.exists(test_path):
        os.remove(test_path)


@pytest.fixture
def test_yaml_path():
    test_path = 'test.yaml'
    yield test_path
    if os.path.exists(test_path):
        os.remove(test_path)


@pytest.fixture
def test_yml_path():
    test_path = 'test.yml'
    yield test_path
    if os.path.exists(test_path):
        os.remove(test_path)


@pytest.fixture
def test_df():
    return pd.DataFrame(
        {
            "gender": [0, 1, 0, 1],
            "height": [157.18518021548246, 166.7731072622863, 162.91821942384928, 173.51448996432848],
            "id": [925, 84, 821, 383]
        }
    )


@pytest.fixture(scope="session")
def rp_logger():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logging.setLoggerClass(RPLogger)
    return logger
