from typing import Dict, Tuple
from abc import ABC, abstractmethod
from dataclasses import dataclass

import pandas as pd
from loguru import logger


class Convertor(ABC):
    """Abstract class for converting fetched schema in Avro, Parquet or Delta formats"""
    def __init__(self, schema, df):
        self.converted_schema, self.preprocessed_df = self._convert_schema_and_df(schema, df)

    @abstractmethod
    def _convert_schema_and_df(self, schema: Dict, df: pd.DataFrame) -> Tuple[Dict, pd.DataFrame]:
        """
        Convert the schema of file to unified format, preprocess dataframe
        """
        pass

    @staticmethod
    def _preprocess_df(schema: Dict, df: pd.DataFrame) -> pd.DataFrame:
        """
        Preprocess data frame, update data types of columns
        """
        if not df.empty:
            for column, data_type in schema.get("fields", {}).items():
                if data_type in ["binary", "date"]:
                    df[column] = df[column].astype("string")
                elif data_type == "int":
                    if any(df[column].isnull()):
                        df[column] = df[column].astype("float64")
                    else:
                        df[column] = df[column].astype("int64")
                elif data_type == "string":
                    df[column] = df[column].astype("string")
            return df
        else:
            return df


@dataclass
class CSVConvertor:
    """
    Class for supporting custom schema for csv files
    """
    df: pd.DataFrame()
    schema = {"fields": {}, "format": "CSV"}


class AvroConvertor(Convertor):
    """
    Class for converting fetched avro schema
    """
    def __init__(self, schema, df):
        super().__init__(schema, df)

    def _convert_schema_and_df(self, schema, df) -> Tuple[Dict, pd.DataFrame]:
        """
        Convert the schema of Avro file to unified format, preprocess dataframe
        """
        converted_schema = dict()
        converted_schema["fields"] = dict()
        for column, data_type in schema.items():
            fields = converted_schema["fields"]
            if "int" in data_type or "long" in data_type or "boolean" in data_type:
                fields[column] = "int"
            elif "float" in data_type or "double" in data_type:
                fields[column] = "float"
            elif "string" in data_type:
                fields[column] = "string"
            elif "bytes" in data_type:
                fields[column] = "string"
            else:
                message = f"It seems that the column - '{column}' has unsupported data type - '{data_type}'"
                logger.error(message)
                raise ValueError(message)
        converted_schema["format"] = "Avro"
        preprocessed_df = self._preprocess_df(converted_schema, df)
        return converted_schema, preprocessed_df
