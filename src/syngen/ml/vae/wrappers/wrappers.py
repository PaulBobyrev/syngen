from typing import Tuple, List, Optional, Dict
from abc import ABC, abstractmethod
from collections import defaultdict
from pathlib import Path

import warnings
import pickle
import tensorflow as tf
from tensorflow.python.data.experimental import AutoShardPolicy
import matplotlib.pyplot as plt
import time
import tqdm
from loguru import logger
import pandas as pd
import numpy as np

from syngen.ml.vae.models.model import CVAE
from syngen.ml.vae.models import Dataset
from syngen.ml.utils import fetch_dataset

warnings.filterwarnings("ignore")

BATCH_SIZE_DEFAULT = 32


class BaseWrapper(ABC):
    """
    Abstract class for wrappers
    """

    def __init__(self):
        self.model = None

    @abstractmethod
    def fit_on_df(
        self,
        df: pd.DataFrame,
        epochs: int,
        columns_subset: List[str] = None
    ):
        pass

    @abstractmethod
    def predict_sampled_df(self, n: int) -> pd.DataFrame:
        pass

    @abstractmethod
    def save_state(self, path: str):
        pass

    @abstractmethod
    def load_state(self, path: str):
        pass


class VAEWrapper(BaseWrapper):
    """Base class that implements end to end train and generation of structured data.

    Attributes
    ----------
    df
    schema
    metadata
    table_name
    paths
    process
    batch_size
    latent_dim
    latent_components

    Methods
    -------
    _pipeline()
        data preprocessing

    _train(dataset, row_subset, epochs)
        train the VAE and save result in model

    display_losses()
        show train losses curve by each feature

    predict_sampled_df(df, n)
        generate new data based on df that consist of n rows and return the result as pd.DataFrame

    predict_less_likely_samples(df, n, temp=0.05, variety=3)
        generate new data based on df that consist of n which has less probability
        computed as log likelihood and return the result as pd.DataFrame
    """

    def __init__(
        self,
        df: pd.DataFrame,
        schema: Optional[Dict],
        metadata: dict,
        table_name: str,
        paths: dict,
        process: str,
        batch_size: int,
        latent_dim: int = 10,
        latent_components: int = 30,
    ):
        super().__init__()
        self.df = df
        self.schema = schema
        self.process = process
        self.batch_size = batch_size
        self.latent_dim = latent_dim
        self.latent_components = latent_components
        self.metadata = metadata
        self.table_name = table_name
        self.vae_resources_path = paths["state_path"]
        self.dataset_pickle_path = paths["dataset_pickle_path"]
        self.fk_kde_path = paths["fk_kde_path"]

    def __post__init__(self):
        if self.process == "train":
            self.dataset = Dataset(
                df=self.df,
                schema=self.schema,
                metadata=self.metadata,
                table_name=self.table_name,
                fk_kde_path=self.fk_kde_path
            )
        elif self.process == "infer":
            self.dataset = fetch_dataset(self.dataset_pickle_path)

    def _pipeline(self):
        self.dataset.set_metadata()
        self.df = self.dataset.pipeline()

        with open(self.dataset_pickle_path, "wb") as f:
            f.write(pickle.dumps(self.dataset))

    def _restore_zero_values(self, df):
        for column in self.dataset.zero_num_column_names:
            if column.endswith("_zero"):
                # remove _zero to get original column name
                num_column_name = column[:-5]
                num_column = df[num_column_name].copy()
                zero_column_mask = df[column].astype("float") >= 0.5
                num_column = num_column.where(zero_column_mask, 0)
                num_zero_values = (num_column == 0).sum()
                df[num_column_name] = num_column
                df = df.drop(column, axis=1)
                logger.info(
                    f"Column {column} has {num_zero_values} ({round(num_zero_values * 100 / len(num_column))}%) "
                    f"zero values generated"
                )
        return df

    def _restore_nan_values(self, df):
        for column in self.dataset.null_num_column_names:
            if column.endswith("_null"):
                # remove _null to get original column name
                num_column_name = column[:-5]
                num_column = df[num_column_name].copy()
                not_null_column_mask = df[column].astype("float64") <= 0.5
                num_column = num_column.where(not_null_column_mask, np.nan)
                df[num_column_name] = num_column
                df = df.drop(column, axis=1)
                num_nan_values = num_column.isna().sum()
                logger.info(
                    f"Column {column} has {num_nan_values} ({round(num_nan_values * 100 / len(num_column))}%) "
                    f"empty values generated."
                )
        return df

    def _restore_nan_labels(self, df):
        for column_name, nan_label in self.dataset.nan_labels_dict.items():
            if nan_label is None:
                nan_label = np.nan
            df[column_name] = df[column_name].fillna(np.nan) if nan_label is None else df[column_name].fillna(nan_label)
        return df

    @abstractmethod
    def _init_model(self):
        pass

    def prepare_dataset(self):
        self.__post__init__()
        self._pipeline()

    def fit_on_df(
        self,
        df: pd.DataFrame,
        epochs: int,
        columns_subset: List[str] = None,  # TODO columns_subset does not work
    ):
        self._init_model()

        if columns_subset is None:
            columns_subset = self.df.columns
        else:
            # if a column is in columns_subset, its null column should also be added if present
            columns_subset += [
                col
                for col in self.df.columns
                if col.endswith(("_null", "_zero")) and (col[:-5] in columns_subset)
            ]

        df = self.df.loc[:, list(set(columns_subset))]

        train_dataset = self._create_batched_dataset(df)
        self.vae = self.model.model

        self.optimizer = self._create_optimizer()
        self.loss_metric = self._create_loss()
        self._train(train_dataset, epochs)

        self.model.model = self.vae
        self.fit_sampler(df.dropna())

    def _train(self, dataset, epochs: int):
        step = self._train_step

        self.feature_losses = defaultdict(list)
        loss_grows_num_epochs = 0
        prev_total_loss = float("inf")
        es_min_delta = 0.005
        es_patience = 10
        pth = Path(self.vae_resources_path)

        for epoch in range(epochs):
            num_batches = 0.0
            total_loss = 0.0
            t1 = time.time()

            # Iterate over the batches of the dataset.
            for i, x_batch_train in tqdm.tqdm(iterable=enumerate(dataset)):
                total_loss += step(x_batch_train)
                num_batches += 1

            mean_loss = np.mean(total_loss / num_batches)
            if mean_loss >= prev_total_loss - es_min_delta:
                loss_grows_num_epochs += 1
            else:
                self.vae.save_weights(str(pth / "vae_best_weights_tmp.ckpt"))
                loss_grows_num_epochs = 0

            logger.info(
                f"epoch: {epoch}, loss: {mean_loss}, time: {time.time()-t1}, sec"
            )

            prev_total_loss = mean_loss
            if loss_grows_num_epochs == es_patience:
                self.vae.load_weights(str(pth / "vae_best_weights_tmp.ckpt"))
                logger.info(
                    f"The loss does not become lower for {loss_grows_num_epochs} epochs in a row. Stopping the training."
                )
                break
            epoch += 1

    # @staticmethod
    def _create_optimizer(self):
        learning_rate = 1e-04 * np.sqrt(self.batch_size / BATCH_SIZE_DEFAULT)
        return tf.keras.optimizers.Adam(learning_rate=learning_rate)

    @staticmethod
    def _create_loss():
        return tf.keras.metrics.Mean()

    def _create_batched_dataset(self, df: pd.DataFrame):
        """Define batched dataset for training vae"""
        transformed_data = self.dataset.transform(df)

        feature_datasets = []
        options = tf.data.Options()
        options.experimental_distribute.auto_shard_policy = AutoShardPolicy.DATA
        for inp in transformed_data:
            dataset = tf.data.Dataset.from_tensor_slices(inp).with_options(options)
            feature_datasets.append(dataset)

        dataset = tf.data.Dataset.zip(tuple(feature_datasets)).with_options(options)
        return dataset.batch(self.batch_size, drop_remainder=True)

    def _train_step(self, batch: Tuple[tf.Tensor]) -> tf.Tensor:
        with tf.GradientTape() as tape:
            self.vae(batch)

            # Compute reconstruction loss
            loss = sum(self.vae.losses)

        self.optimizer.minimize(
            loss=loss, var_list=[self.vae.trainable_weights], tape=tape
        )
        self.loss_metric(loss)
        return loss

    def display_losses(self):
        for name, l in self.feature_losses.items():
            plt.plot(l, label=name)

        plt.legend()
        plt.ylim(0, 10)
        return plt.show()

    def fit_sampler(self, df: pd.DataFrame):
        self.model.fit_sampler(df)

    def predict_sampled_df(self, n: int) -> pd.DataFrame:
        sampled_df = self.model.sample(n)
        sampled_df = self._restore_nan_values(sampled_df)
        sampled_df = self._restore_zero_values(sampled_df)
        return sampled_df

    def predict_less_likely_samples(
        self, df: pd.DataFrame, n: int, temp=0.05, variaty=3
    ):
        self.fit_sampler(df)
        return self.model.less_likely_sample(n, temp, variaty)

    def save_state(self, path: str):
        self.model.save_state(path)
        logger.info(f"Saved VAE state in {path}")

    def load_state(self, path: str):
        try:
            with open(path + "/model_dataset.pkl", "rb") as f:
                self.dataset = pickle.loads(f.read())

            self._init_model()

            state = self.model.load_state(path)

        except (FileNotFoundError, ValueError):
            raise FileNotFoundError("Missing file with VAE state")

        logger.info(f"Loaded VAE state from {path}")
        return state


class VanillaVAEWrapper(VAEWrapper):
    """
    Class that implements end to end train and generation of structured data by CVAE as a model.

    Attributes
    ----------
    model : CVAE
        final model that we will use to generate new data
    """

    def _init_model(self):
        latent_dim = min(self.latent_dim, int(len(self.dataset.columns) / 2))

        self.model = CVAE(
            self.dataset,
            batch_size=self.batch_size,
            latent_dim=latent_dim,
            latent_components=min(self.latent_components, latent_dim * 2),
            intermediate_dim=128,
        )

        self.model.build_model()
