from typing import Optional
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import click
from loguru import logger

from syngen.ml.worker import Worker


@click.command()
@click.option("--metadata_path", type=str, default=None, help="Path to the metadata file")
@click.option("--source", type=str, default=None, help="Path to the table that you want to use as a reference")
@click.option("--table_name", type=str, default=None, help="Arbitrary string to name the directories")
@click.option("--epochs", default=10, type=click.IntRange(1),
              help="Number of trained epochs. If absent, it's defaulted to 10")
@click.option("--drop_null", default=False, type=click.BOOL,
              help="Flag which set whether to drop rows with at least one missing value. "
                   "If absent, it's defaulted to False")
@click.option("--row_limit", default=None, type=click.IntRange(1),
              help="Number of rows to train over. A number less than the original table length will randomly subset "
                   "the specified rows number")
@click.option("--print_report", default=False, type=click.BOOL,
              help="Whether to print quality report. Might require significant time "
                   "for big generated tables (>1000 rows). If absent, it's defaulted to False")
@click.option("--batch_size", default=32, type=click.IntRange(1),
              help="Number of rows that goes in one batch. This parameter can help to control memory consumption.")
def launch_train(
    metadata_path: Optional[str],
    source: Optional[str],
    table_name: Optional[str],
    epochs: int,
    drop_null: bool,
    row_limit: Optional[int],
    print_report: bool,
    batch_size: int = 32,
):
    """
    Launch the work of training process

    Parameters
    ----------
    metadata_path
    source
    table_name
    epochs
    drop_null
    row_limit
    print_report
    batch_size
    -------

    """
    if not metadata_path and not source:
        raise AttributeError("It seems that the information of metadata_path or source is absent. "
                             "Please provide either the information of metadata_path or "
                             "the information of source and table_name.")
    if metadata_path:
        if source:
            logger.warning("The information of metadata_path was provided. "
                           "In this case the information of source will be ignored.")
        if table_name:
            logger.warning("The information of metadata_path was provided. "
                           "In this case the information of table_name will be ignored.")
            table_name = None
        if not metadata_path.endswith(('.yaml', '.yml')):
            raise NotImplementedError("This format for metadata_path is not supported. "
                                      "Please provide metadata_path in '.yaml' or '.yml' format")
    if not metadata_path:
        if source and not table_name:
            raise AttributeError("It seems that the information of table_name is absent. "
                                 "In the case the information of metadata_path is absent, "
                                 "the information of source and table_name should be provided.")
        if table_name and not source:
            raise AttributeError("It seems that the information of source is absent. "
                                 "In the case the information of metadata_path is absent, "
                                 "the information of source and table_name should be provided.")
    settings = {
        "source": source,
        "epochs": epochs,
        "drop_null": drop_null,
        "row_limit": row_limit,
        "batch_size": batch_size,
        "print_report": print_report
    }
    worker = Worker(
        table_name=table_name,
        metadata_path=metadata_path,
        settings=settings
    )
    worker.launch_train()


if __name__ == "__main__":
    launch_train()
