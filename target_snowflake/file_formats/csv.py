"""CSV file format functions"""
import gzip
import json
import os

from typing import Callable, Dict, List
from tempfile import mkstemp

from target_snowflake import flattening


def create_copy_sql(table_name: str,
                    stage_name: str,
                    s3_key: str,
                    file_format_name: str,
                    columns: List,
                    restrict_file_pattern: bool = False,
                    ) -> str:
    """Generate a CSV compatible snowflake COPY INTO command"""
    p_columns = ', '.join([c['name'] for c in columns])

    select_statement = select_from_stage(columns, file_format_name, s3_key, stage_name, restrict_file_pattern)

    return f"COPY INTO {table_name} ({p_columns}) FROM ({select_statement})"


def create_merge_sql(table_name: str,
                     stage_name: str,
                     s3_key: str,
                     file_format_name: str,
                     columns: List,
                     pk_merge_condition: str,
                     restrict_file_pattern: bool = False,
                     ) -> str:
    """Generate a CSV compatible snowflake MERGE INTO command"""
    p_update = ', '.join([f"{c['name']}=s.{c['name']}" for c in columns])
    p_insert_cols = ', '.join([c['name'] for c in columns])
    p_insert_values = ', '.join([f"s.{c['name']}" for c in columns])

    select_statement = select_from_stage(columns, file_format_name, s3_key, stage_name, restrict_file_pattern)

    return f"MERGE INTO {table_name} t USING ({select_statement}) s " \
           f"ON {pk_merge_condition} " \
           f"WHEN MATCHED THEN UPDATE SET {p_update} " \
           "WHEN NOT MATCHED THEN " \
           f"INSERT ({p_insert_cols}) " \
           f"VALUES ({p_insert_values})"


def select_from_stage(columns, file_format_name, s3_key, stage_name, restrict_file_pattern=False):
    column_expressions = []
    idx = 0
    for column in columns:
        expr = column['value']
        if not expr:
            idx += 1
            expr = f"{column['trans']}(${idx})"
        full_expr = ' '.join([expr, column['name']])
        column_expressions.append(full_expr)

    p_source_columns = ', '.join(column_expressions)

    select_options = {
        'FILE_FORMAT': file_format_name,
    }
    if restrict_file_pattern:
        # Include the s3_key as a pattern, to exclude other keys that have this key as a prefix
        select_options['PATTERN'] = s3_key
    options_clause = ', '.join([f"{k} => '{v}'" for k, v in select_options.items()])

    select_from_stage = f"SELECT {p_source_columns} FROM '@{stage_name}/{s3_key}' ({options_clause})"
    return select_from_stage


def record_to_csv_line(record: dict,
                       schema: dict,
                       data_flattening_max_level: int = 0) -> str:
    """
    Transforms a record message to a CSV line

    Args:
        record: Dictionary that represents a csv line. Dict key is column name, value is the column value
        schema: JSONSchema of the record
        data_flattening_max_level: Max level of auto flattening if a record message has nested objects. (Default: 0)

    Returns:
        string of csv line
    """
    flatten_record = flattening.flatten_record(record, schema, max_level=data_flattening_max_level)

    return ','.join(
        [
            json.dumps(flatten_record[column], ensure_ascii=False) if column in flatten_record and (
                    flatten_record[column] == 0 or flatten_record[column]) else ''
            for column in schema
        ]
    )


def write_records_to_file(outfile,
                          records: Dict,
                          schema: Dict,
                          record_to_csv_line_transformer: Callable,
                          data_flattening_max_level: int = 0) -> None:
    """
    Writes a record message to a given file

    Args:
        outfile: An open file object
        records: List of dictionaries that represents a batch of singer record messages
        schema: JSONSchema of the records
        record_to_csv_line_transformer: Function that transforms dictionary to a CSV string line
        data_flattening_max_level: Max level of auto flattening if a record message has nested objects. (Default: 0)

    Returns:
        None
    """
    for record in records.values():
        csv_line = record_to_csv_line_transformer(record, schema, data_flattening_max_level)
        outfile.write(bytes(csv_line + '\n', 'UTF-8'))


def records_to_file(records: Dict,
                    schema: Dict,
                    suffix: str = 'csv',
                    prefix: str = 'batch_',
                    compression: bool = False,
                    dest_dir: str = None,
                    data_flattening_max_level: int = 0):
    """
    Transforms a list of dictionaries with records messages to a CSV file

    Args:
        records: List of dictionaries that represents a batch of singer record messages
        schema: JSONSchema of the records
        suffix: Generated filename suffix
        prefix: Generated filename prefix
        compression: Gzip compression enabled or not (Default: False)
        dest_dir: Directory where the CSV file will be generated. (Default: OS specificy temp directory)
        data_flattening_max_level: Max level of auto flattening if a record message has nested objects. (Default: 0)

    Returns:
        Absolute path of the generated CSV file
    """
    if dest_dir:
        os.makedirs(dest_dir, exist_ok=True)

    if compression:
        file_suffix = f'.{suffix}.gz'
    else:
        file_suffix = f'.{suffix}'

    filedesc, filename = mkstemp(suffix=file_suffix, prefix=prefix, dir=dest_dir)

    # Using gzip or plain file object
    if compression:
        with open(filedesc, 'wb') as outfile:
            with gzip.GzipFile(filename=filename, mode='wb',fileobj=outfile) as gzipfile:
                write_records_to_file(gzipfile, records, schema, record_to_csv_line, data_flattening_max_level)
    else:
        with open(filedesc, 'wb') as outfile:
            write_records_to_file(outfile, records, schema, record_to_csv_line, data_flattening_max_level)

    return filename
