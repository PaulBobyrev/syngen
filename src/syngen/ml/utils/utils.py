from typing import List, Dict
from dateutil.parser import parse
import pickle
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
from slugify import slugify


def get_date_columns(df: pd.DataFrame, str_columns: List[str]):
    # TODO: extend pattern to more formats
    # pattern = r'\d{2}(\.|/|\-)\d{2}(\.|/|\-)(\d{2}|\d{4})'
    # pattern = r"\s{0,1}\d+[-/\\:]\s{0,1}\d+[-/\\:]\s{0,1}\d+"

    def len_filter(x):
        return (x.str.len() > 500).any()

    def date_finder(x, fuzzy=False):
        x_wo_na = x.dropna()
        count = 0
        for x in x_wo_na.values:
            try:
                parse(x, fuzzy=fuzzy)
                count += 1
            except (ValueError, OverflowError):
                continue
        if count > len(x_wo_na) * 0.8:
            return 1
        else:
            return np.nan

    data_subset = df[str_columns]
    data_subset = data_subset if data_subset.empty else data_subset.loc[:, data_subset.apply(len_filter)]
    long_text_columns = data_subset.columns
    str_columns = [i for i in str_columns if i not in long_text_columns]
    date_columns = df[str_columns].apply(date_finder).dropna()

    if isinstance(date_columns, pd.DataFrame):
        names = date_columns.columns
    elif isinstance(date_columns, pd.Series):
        names = date_columns.index
    else:
        names = []
    return set(names)


def get_nan_labels(df: pd.DataFrame) -> dict:
    """Get labels that represent nan values in float/int columns

    Args:
        df (pd.DataFrame): table data

    Returns:
        dict: dict that maps nan str label to column name
    """
    columns_nan_labels = {}
    object_columns = df.select_dtypes(include=[pd.StringDtype(), "object"]).columns
    for column in object_columns:
        str_values = []
        float_val = None
        for val in df[column].unique():
            try:
                float_val = float(val)
            except (TypeError, ValueError):
                str_values.append(val)
        if (
                (float_val is not None)
                and (not np.isnan(float_val))
                and len(str_values) == 1
        ):
            nan_label = str_values[0]
            columns_nan_labels[column] = nan_label

    return columns_nan_labels


def nan_labels_to_float(df: pd.DataFrame, columns_nan_labels: dict) -> pd.DataFrame:
    """Replace str nan labels in float/int columns with actual np.nan and casting the column to float type.

    Args:
        df (pd.DataFrame): table data

    Returns:
        pd.DataFrame: DataFrame with str NaN labels in float/int columns replaced with np.nan
    """
    df_with_nan = df.copy()
    for column, label in columns_nan_labels.items():
        df_with_nan[column] = pd.to_numeric(
            df_with_nan[column].where(df_with_nan[column] != label, np.nan)
        )  # casting from object to int/float
    return df_with_nan


def get_tmp_df(df):
    tmp_col_len_min = float("inf")
    tmp_cols = {}
    for col in df.columns:
        tmp_cols[col] = pd.Series(df[col].dropna().values)
        tmp_col_len = len(tmp_cols[col])
        if tmp_col_len < tmp_col_len_min:
            tmp_col_len_min = tmp_col_len
    return pd.DataFrame(tmp_cols).iloc[:tmp_col_len_min, :]


def fillnan(df, str_columns, float_columns, categ_columns):
    for c in str_columns | categ_columns:
        df[c] = df[c].fillna("NaN")

    return df


def fetch_dataset(dataset_pickle_path: str):
    """
    Deserialize and return the object of class Dataset
    """
    with open(dataset_pickle_path, "rb") as f:
        return pickle.loads(f.read())


def slugify_attribute(**kwargs):
    """
    Slugify the value of the attribute of the instance
    and set it to the new attribute
    """
    def wrapper(function):
        def inner_wrapper(*args):
            object_, *other = args
            for attribute, new_attribute in kwargs.items():
                fetched_attribute = object_.__getattribute__(attribute)
                value_of_new_attribute = slugify(fetched_attribute)
                object_.__setattr__(new_attribute, value_of_new_attribute)
            return function(*args)
        return inner_wrapper
    return wrapper


def slugify_parameters(exclude_params=()):
    """
    Slugify the values of parameters, excluding specified parameters
    """
    def wrapper(function):
        def inner_wrapper(**kwargs):
            updated_kwargs = {}
            for key, value in kwargs.items():
                if key in exclude_params:
                    updated_kwargs[key] = value
                else:
                    updated_kwargs[key] = slugify(value)
            return function(**updated_kwargs)
        return inner_wrapper

    return wrapper


def inverse_dict(dictionary: Dict) -> Dict:
    """
    Swap keys and values in the dictionary
    """
    return dict(zip(dictionary.values(), dictionary.keys()))


def trim_string(col):
    if isinstance(col.dtype, str):
        return col.str.slice(stop=10 * 1024)
    else:
        return col


def convert_to_time(timestamp):
    """
    Convert timestamp to datetime
    """
    timestamp = int(timestamp * 1e-9)
    if timestamp < 0:
        return datetime(1970, 1, 1) + timedelta(seconds=timestamp)
    else:
        return datetime.utcfromtimestamp(timestamp)
