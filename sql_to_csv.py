import re
import csv
import argparse
import os
from typing import List, TextIO


def parse_create_table(line: str) -> str:
    """Extract table name from CREATE TABLE statement."""
    match = re.search(r'CREATE TABLE\s+[`"]?(\w+)[`"]?', line, re.IGNORECASE)
    return match.group(1) if match else None


def parse_insert_values(line: str) -> List[tuple]:
    """Parse INSERT INTO statement and extract values."""
    # Handle both INSERT INTO and REPLACE INTO
    if not ('VALUES' in line or 'values' in line):
        return []

    # Extract the values portion of the line
    values_part = line.split('VALUES', 1)[-1].split('value', 1)[-1].strip()

    # Match values between parentheses
    values_match = re.findall(r'\(((?:[^()]|\([^()]*\))*)\)', values_part)

    if not values_match:
        return []

    rows = []
    for value_str in values_match:
        # Split by comma but not within quotes or nested parentheses
        row = []
        current = ''
        in_quotes = False
        quote_char = None
        paren_level = 0

        for char in value_str + ',':
            if char in '"\'':
                if not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif char == quote_char:
                    in_quotes = False
                    quote_char = None
            elif char == '(' and not in_quotes:
                paren_level += 1
            elif char == ')' and not in_quotes:
                paren_level -= 1
            elif char == ',' and not in_quotes and paren_level == 0:
                row.append(current.strip())
                current = ''
                continue
            current += char

        # Clean up each value
        row = [_clean_value(val.strip()) for val in row if val.strip()]
        if row:
            rows.append(tuple(row))

    return rows


def _clean_value(val: str) -> str:
    """Clean up a SQL value."""
    # Handle NULL values
    if val.upper() == 'NULL':
        return ''

    # Remove quotes if present
    if (val.startswith('"') and val.endswith('"')) or \
       (val.startswith("'") and val.endswith("'")):
        val = val[1:-1]

    # Handle MySQL escapes
    val = val.replace('\\\\', '\\').replace("\\'", "'").replace('\\"', '"')

    return val


def get_column_names(line: str) -> List[str]:
    """Extract column names from CREATE TABLE statement."""
    # Find the content between parentheses
    match = re.search(r'\((.*)\)', line, re.DOTALL)
    if not match:
        return []

    columns = []
    in_constraint = False

    for column_def in match.group(1).split(','):
        column_def = column_def.strip()

        # Skip constraints, keys, etc.
        if any(keyword in column_def.upper() for keyword in
               ['CONSTRAINT', 'PRIMARY KEY', 'FOREIGN KEY', 'KEY', 'INDEX', 'UNIQUE']):
            continue

        # Extract column name (handles quoted and unquoted names)
        column_match = re.search(r'^[`"]?(\w+)[`"]?\s+\w+', column_def.strip())
        if column_match:
            columns.append(column_match.group(1))

    return columns


def ensure_dir(directory):
    """Create directory if it doesn't exist."""
    if not os.path.exists(directory):
        os.makedirs(directory)


def convert_sql_to_csv(sql_file: TextIO, output_dir: str = '.') -> None:
    """Convert SQL dump file to CSV format."""
    ensure_dir(output_dir)
    current_table = None
    columns = []
    csv_writer = None
    csv_file = None
    buffer = ''

    for line in sql_file:
        line = line.strip()

        # Skip comments and empty lines
        if not line or line.startswith('--') or line.startswith('/*') or line.startswith('SET '):
            continue

        # Buffer the line for multi-line statements
        buffer += ' ' + line

        # Process complete statements
        if buffer.strip().endswith(';'):
            full_statement = buffer.strip().rstrip(';')
            buffer = ''

            # Handle CREATE TABLE
            if full_statement.upper().startswith('CREATE TABLE'):
                if csv_file:
                    csv_file.close()

                current_table = parse_create_table(full_statement)
                columns = get_column_names(full_statement)

                if current_table and columns:
                    csv_file = open(
                        f'{output_dir}/{current_table}.csv', 'w', newline='', encoding='utf-8')
                    csv_writer = csv.writer(csv_file)
                    csv_writer.writerow(columns)

            # Handle INSERT/REPLACE statements
            elif any(full_statement.upper().startswith(prefix) for prefix in ['INSERT INTO', 'REPLACE INTO']) \
                    and current_table and csv_writer:
                rows = parse_insert_values(full_statement)
                csv_writer.writerows(rows)

    if csv_file:
        csv_file.close()


def main():
    parser = argparse.ArgumentParser(
        description='Convert MySQL dump file to CSV format')
    parser.add_argument('sql_file', type=str, help='Input SQL dump file')
    parser.add_argument('--output-dir', type=str, default='.',
                        help='Output directory for CSV files (default: current directory)')

    args = parser.parse_args()

    with open(args.sql_file, 'r', encoding='utf-8') as sql_file:
        convert_sql_to_csv(sql_file, args.output_dir)


if __name__ == '__main__':
    main()
