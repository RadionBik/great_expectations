import os

import pandas as pd
from ruamel import yaml

import great_expectations as ge
from great_expectations.checkpoint import SimpleCheckpoint
from great_expectations.core.batch import BatchRequest, RuntimeBatchRequest
from great_expectations.core.util import get_or_create_spark_application
from great_expectations.data_context import BaseDataContext
from great_expectations.data_context.types.base import (
    DataContextConfig,
    DatasourceConfig,
    FilesystemStoreBackendDefaults,
)
from great_expectations.util import gen_directory_tree_str

SKIP_IN_TEST = True

spark = get_or_create_spark_application(
    # spark_config={
    #     # TODO: is this spark_config required?
    #     "spark.sql.catalogImplementation": "hive",
    #     "spark.executor.memory": "450m",
    #     # "spark.driver.allowMultipleContexts": "true",  # This directive does not appear to have any effect.
    # }
)

# TODO: ABOVE THIS LINE HAS NOT BEEN CLEANED UP
# ---------------------------------------------

##################
# BEGIN CONTENT
##################

# 1. Install Great Expectations
# %pip install great-expectations
# Imports

# 2. Set up Great Expectations
# In-memory DataContext using DBFS and FilesystemStoreBackendDefaults

# This root directory is for use in Databricks
root_directory = "/dbfs/great_expectations/"

# For testing purposes, we change the root_directory to an ephemeral location
root_directory = os.path.join(os.getcwd(), "dbfs_temp_directory")

data_context_config = DataContextConfig(
    store_backend_defaults=FilesystemStoreBackendDefaults(
        root_directory=root_directory
    ),
)
context = BaseDataContext(project_config=data_context_config)

# Check the stores were initialized
uncommitted_directory = os.path.join(root_directory, "uncommitted")
assert os.listdir(root_directory) == ["checkpoints", "expectations", "uncommitted"]
assert os.listdir(uncommitted_directory) == ["validations"]

# 3. Prepare your data (File & Dataframe)

filename = "yellow_trip_data_sample_2019-01.csv"
pandas_df = pd.read_csv(os.path.join(os.getcwd(), "data", filename))
df = spark.createDataFrame(data=pandas_df)

assert len(pandas_df) == df.count() == 10000
assert len(pandas_df.columns) == len(df.columns) == 18


# 4. Connect to your data (File)

# CODE vvvvv vvvvv
my_spark_datasource_config = """
name: insert_your_datasource_name_here
class_name: Datasource
execution_engine:
  class_name: SparkDFExecutionEngine
data_connectors:
  insert_your_data_connector_name_here:
    module_name: great_expectations.datasource.data_connector
    class_name: InferredAssetFilesystemDataConnector
    base_directory: /dbfs/example_data/nyctaxi/tripdata/yellow/
    default_regex:
      pattern: (.*)
      group_names:
        - data_asset_name
"""

# For this test script, change base_directory to location where test runner data is located
my_spark_datasource_config = my_spark_datasource_config.replace(
    "/dbfs/example_data/nyctaxi/tripdata/yellow/", "data"
)

context.test_yaml_config(my_spark_datasource_config)

context.add_datasource(**yaml.load(my_spark_datasource_config))

batch_request = BatchRequest(
    datasource_name="insert_your_datasource_name_here",
    data_connector_name="insert_your_data_connector_name_here",
    data_asset_name="yellow_tripdata_2019-01.csv",
)
# CODE ^^^^^ ^^^^^

# ASSERTIONS vvvvv vvvvv
my_spark_datasource_config_dict = {
    "name": "insert_your_datasource_name_here",
    "class_name": "Datasource",
    "module_name": "great_expectations.datasource",
    "execution_engine": {
        "module_name": "great_expectations.execution_engine",
        "class_name": "SparkDFExecutionEngine",
    },
    "data_connectors": {
        "insert_your_data_connector_name_here": {
            "module_name": "great_expectations.datasource.data_connector",
            "class_name": "InferredAssetFilesystemDataConnector",
            "base_directory": "data",
            "default_regex": {"pattern": "(.*)", "group_names": ["data_asset_name"]},
        }
    },
}
assert len(context.list_datasources()) == 1
assert context.list_datasources() == [my_spark_datasource_config_dict]
assert sorted(
    context.get_available_data_asset_names()["insert_your_datasource_name_here"][
        "insert_your_data_connector_name_here"
    ]
) == sorted(
    [
        "yellow_trip_data_sample_2019-01.csv",
        "yellow_trip_data_sample_2019-02.csv",
        "yellow_trip_data_sample_2019-03.csv",
    ]
)
available_data_asset_names = context.datasources[
    "insert_your_datasource_name_here"
].get_available_data_asset_names(
    data_connector_names="insert_your_data_connector_name_here"
)[
    "insert_your_data_connector_name_here"
]
assert len(available_data_asset_names) == 3
# assert context.get_batch_list(batch_request=batch_request) == []
# ASSERTIONS ^^^^^ ^^^^^

# TODO: BELOW THIS LINE HAS NOT BEEN CLEANED UP
# ---------------------------------------------

print("DEBUG ==============================")
print(
    context.get_available_data_asset_names(
        datasource_names=["insert_your_datasource_name_here"]
    )
)
print(context.get_batch_list(batch_request=batch_request))
print(
    context.get_batch_list(
        datasource_name="insert_your_datasource_name_here",
        data_connector_name="insert_your_data_connector_name_here",
        data_asset_name="yellow_tripdata_2019-01.csv",
    )
)


# TODO: Why am I getting an error here and no batches above even with a data_asset_name provided?
# Traceback (most recent call last):
#   File "/private/var/folders/ds/hn_qpp1n6y3fz28clrkfmpsr0000gn/T/pytest-of-anthonyburdi/pytest-103/test_docs_tests_integration_do0/test_script.py", line 167, in <module>
#     expectation_suite_name=expectation_suite_name,
#   File "/Users/anthonyburdi/src/ge/great_expectations/great_expectations/data_context/data_context.py", line 1868, in get_validator
#     batch_definition = batch_list[-1].batch_definition
# IndexError: list index out of range
# 5. Create expectations (File)
# CODE vvvvv vvvvv
expectation_suite_name = "insert_your_expectation_suite_name_here"
context.create_expectation_suite(
    expectation_suite_name=expectation_suite_name, overwrite_existing=True
)
validator = context.get_validator(
    batch_request=batch_request,
    expectation_suite_name=expectation_suite_name,
)

validator.expect_column_values_to_not_be_null(column="passenger_count")

validator.expect_column_values_to_be_between(
    column="congestion_surcharge", min_value=0, max_value=1000
)

validator.save_expectation_suite(discard_failed_expectations=False)
# CODE ^^^^^ ^^^^^
# ASSERTIONS vvvvv vvvvv
assert context.list_expectation_suite_names() == [expectation_suite_name]
# ASSERTIONS ^^^^^ ^^^^^

# Working above this line ---------------------------------------------
print("Everything that has been cleaned up ran successfully")
print("DEBUG ==============================")

# TODO: BELOW THIS LINE HAS NOT BEEN CLEANED UP
# ---------------------------------------------

# 6. Validate your data (File)
# CODE vvvvv vvvvv
# CODE ^^^^^ ^^^^^
# ASSERTIONS vvvvv vvvvv
# ASSERTIONS ^^^^^ ^^^^^

# 7. Build and view Data Docs (File)
# CODE vvvvv vvvvv
# CODE ^^^^^ ^^^^^
# ASSERTIONS vvvvv vvvvv
# ASSERTIONS ^^^^^ ^^^^^

# 4. Connect to your data (Dataframe)
# CODE vvvvv vvvvv
# CODE ^^^^^ ^^^^^
# ASSERTIONS vvvvv vvvvv
# ASSERTIONS ^^^^^ ^^^^^

# 5. Create expectations (Dataframe)
# CODE vvvvv vvvvv
# CODE ^^^^^ ^^^^^
# ASSERTIONS vvvvv vvvvv
# ASSERTIONS ^^^^^ ^^^^^

# 6. Validate your data (Dataframe)
# CODE vvvvv vvvvv
# CODE ^^^^^ ^^^^^
# ASSERTIONS vvvvv vvvvv
# ASSERTIONS ^^^^^ ^^^^^

# 7. Build and view Data Docs (Dataframe)
# CODE vvvvv vvvvv
# CODE ^^^^^ ^^^^^
# ASSERTIONS vvvvv vvvvv
# ASSERTIONS ^^^^^ ^^^^^

# TODO: BELOW THIS LINE HAS NOT BEEN CLEANED UP
# ---------------------------------------------


# 4. Connect to your data (Dataframe)
# Add a Datasource to our DataContext with data in a spark dataframe using RuntimeDataConnector and RuntimeBatchRequest with SparkDFExecutionEngine
#
#     (Use one of the available sample Databricks datasets to make this easily runnable as a tutorial)
# Example RuntimeDataConnector for use with a dataframe batch
# TODO: DatasourceConfig is not accepted by DataContext.add_datasource
# my_spark_datasource_config = DatasourceConfig(
#     class_name="Datasource",
#     execution_engine={"class_name": "SparkDFExecutionEngine"},
#     data_connectors={
#         "insert_your_runtime_data_connector_name_here": {
#             "module_name": "great_expectations.datasource.data_connector",
#             "class_name": "RuntimeDataConnector",
#             "batch_identifiers": [
#                 "some_key_maybe_pipeline_stage",
#                 "some_other_key_maybe_run_id"
#             ]
#         }
#     }
# )
# TODO: Consider changing this to use test_yaml_config() as in: https://github.com/great-expectations/great_expectations/blob/develop/tests/integration/docusaurus/connecting_to_your_data/filesystem/spark_python_example.py
my_spark_datasource_config = {
    "name": "insert_your_datasource_name_here",
    "class_name": "Datasource",
    "execution_engine": {"class_name": "SparkDFExecutionEngine"},
    "data_connectors": {
        "insert_your_runtime_data_connector_name_here": {
            "module_name": "great_expectations.datasource.data_connector",
            "class_name": "RuntimeDataConnector",
            "batch_identifiers": [
                "some_key_maybe_pipeline_stage",
                "some_other_key_maybe_run_id",
            ],
        }
    },
}

context.test_yaml_config(yaml.dump(my_spark_datasource_config))

context.add_datasource(**my_spark_datasource_config)


assert len(context.list_datasources()) == 1
assert context.list_datasources() == [
    {
        "module_name": "great_expectations.datasource",
        "class_name": "Datasource",
        "execution_engine": {
            "module_name": "great_expectations.execution_engine",
            "class_name": "SparkDFExecutionEngine",
        },
        "data_connectors": {
            "insert_your_runtime_data_connector_name_here": {
                "class_name": "RuntimeDataConnector",
                "batch_identifiers": [
                    "some_key_maybe_pipeline_stage",
                    "some_other_key_maybe_run_id",
                ],
                "module_name": "great_expectations.datasource.data_connector",
            }
        },
        "name": "insert_your_datasource_name_here",
    }
]


batch_request_from_dataframe = RuntimeBatchRequest(
    datasource_name="insert_your_datasource_name_here",
    data_connector_name="insert_your_runtime_data_connector_name_here",
    # data_asset_name="<YOUR_MEANGINGFUL_NAME>",  # This can be anything that identifies this data_asset for you
    data_asset_name="example_data_asset",
    batch_identifiers={
        "some_key_maybe_pipeline_stage": "prod",
        "some_other_key_maybe_run_id": "20211231-007",
    },
    runtime_parameters={"batch_data": df},  # Your dataframe goes here
)


# TODO: load data from local csv path, in DBFS. Here we will need to have two versions, one for display to the user and one for getting the data from our test runner
# batch_request_from_path =


# 3. Create expectations
#
#     Use a Validator and your batch of data to create an expectation suite interactively
#
expectation_suite_name = "insert_your_expectation_suite_name_here"
context.create_expectation_suite(
    expectation_suite_name=expectation_suite_name, overwrite_existing=True
)
validator = context.get_validator(
    batch_request=batch_request_from_dataframe,
    expectation_suite_name=expectation_suite_name,
)

# # TODO: Getting errors here, when trying to use a validator:
# # print(validator.head())
# # Traceback (most recent call last):
# #   File "/private/var/folders/ds/hn_qpp1n6y3fz28clrkfmpsr0000gn/T/pytest-of-anthonyburdi/pytest-39/test_docs_tests_integration_do0/test_script.py", line 181, in <module>
# #     print(validator.head())
# #   File "/Users/anthonyburdi/src/ge/great_expectations/great_expectations/validator/validator.py", line 1620, in head
# #     "fetch_all": fetch_all,
# #   File "/Users/anthonyburdi/src/ge/great_expectations/great_expectations/validator/validator.py", line 364, in get_metric
# #     return self.get_metrics({"_": metric})["_"]
# #   File "/Users/anthonyburdi/src/ge/great_expectations/great_expectations/validator/validator.py", line 359, in get_metrics
# #     for (metric_name, metric_configuration) in metrics.items()
# #   File "/Users/anthonyburdi/src/ge/great_expectations/great_expectations/validator/validator.py", line 359, in <dictcomp>
# #     for (metric_name, metric_configuration) in metrics.items()
# # KeyError: ('table.head', 'batch_id=b04c0ba4d1537a604c8f63fe890a44cb', '04166707abe073177c1dd922d3584468')
#
# print("DEBUG ================================================")
# print("context.get_batch_list(batch_request=batch_request_from_dataframe)")
# batch_list = context.get_batch_list(batch_request=batch_request_from_dataframe)
# print(batch_list)
# print("batch_list[0]---------------------------------")
# print(batch_list[0])
# print("batch_list[0]----------------------------------")
# print(len(batch_list))
# print("DEBUG ================================================")
# print(batch_request_from_dataframe)
# print("DEBUG ================================================")
# print("validator.batches")
# print(validator.batches)
# print("DEBUG ================================================")
# print("validator.active_batch")
# print(validator.active_batch)
# print("DEBUG ================================================")
# print("validator.active_batch_id")
# print(validator.active_batch_id)
# print("DEBUG ================================================")
# print("assertion========================")
# # This assertion fails, the "data" key shows a different instance, and batch_data
#
# # batch_list[0]
# # "data": "<great_expectations.execution_engine.sparkdf_batch_data.SparkDFBatchData object at 0x7f93cef23710>",
# # "batch_data": "<class 'pyspark.sql.dataframe.DataFrame'>"
#
# # validator.active_batch
# # "data": "<great_expectations.execution_engine.sparkdf_batch_data.SparkDFBatchData object at 0x7f93cef061d0>",
# # "batch_data": "<class 'str'>"
# # assert validator.active_batch == batch_list[0]
# print("assertion========================")

print(validator.head())

# validator.expect_column_values_to_not_be_null(column="vendor_id")
# validator.expect_column_values_to_be_between(column="congestion_surcharge", min_value=0, max_value=1000)
# validator.expect_column_values_to_not_be_null(column="a")
# validator.expect_column_values_to_be_between(column="b", min_value=1, max_value=10)


# Take a look at your suite
print(validator.get_expectation_suite(discard_failed_expectations=False))
# Save your suite to your expectation store
validator.save_expectation_suite(discard_failed_expectations=False)

# 4. Validate your data
#
#     Create a Checkpoint in-memory with your RuntimeBatchRequest as one of the validations and run it using Checkpoint.run()
#
#     View data docs

print("DEBUG =========================")
print("Hello I'm trying to do checkpoints now")
print("DEBUG =========================")


checkpoint_name = "insert_your_checkpoint_name_here"
# checkpoint_config = {
#     "class_name": "SimpleCheckpoint",
#     "validations": [
#         {
#             "batch_request": batch_request_from_dataframe,
#             "expectation_suite_name": expectation_suite_name,
#         }
#     ],
# }
# checkpoint = SimpleCheckpoint(
#     name=checkpoint_name, data_context=context, **checkpoint_config
# )
# checkpoint_result = checkpoint.run()

yaml_config = f"""
name: {checkpoint_name}
config_version: 1.0
class_name: SimpleCheckpoint
run_name_template: "%Y%m%d-%H%M%S-my-run-name-template"
"""
print(yaml_config)
my_checkpoint = context.test_yaml_config(yaml_config=yaml_config)
context.add_checkpoint(**yaml.load(yaml_config))

print(context.list_checkpoints())

checkpoint_result = context.run_checkpoint(
    checkpoint_name=checkpoint_name,
    validations=[
        {
            "batch_request": batch_request_from_dataframe,
            "expectation_suite_name": expectation_suite_name,
        }
    ],
)
print("Checkpoint result")
print(checkpoint_result)

context.build_data_docs()

validation_result_identifier = checkpoint_result.list_validation_result_identifiers()[0]

# Should this check the full tree?
# print(os.listdir(root_directory))
# print(os.listdir(os.path.join(root_directory, "uncommitted")))
data_docs_local_site_path = os.path.join(
    root_directory, "uncommitted", "data_docs", "local_site"
)
# print(os.listdir(os.path.join(data_docs_local_site_path)))
# print(os.listdir(os.path.join(data_docs_local_site_path, "validations", expectation_suite_name)))
# print(os.listdir(os.path.join(data_docs_local_site_path, "expectations")))
print(gen_directory_tree_str(root_directory))

print(os.listdir(data_docs_local_site_path))
assert sorted(os.listdir(data_docs_local_site_path)) == sorted(
    ["index.html", "expectations", "validations", "static"]
)
assert os.listdir(os.path.join(data_docs_local_site_path, "validations")) == [
    expectation_suite_name
], "Validation was not written successfully to Data Docs"