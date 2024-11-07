# SQL Dump to CSV Converter

Simple Python script to convert MySQL dump files into CSV format. Creates separate CSV files for each table in the dump.

## Requirements
- Python 3.x

## Usage
```bash
python sql_to_csv.py dump.sql --output-dir output_folder
```

## Features
- Handles MySQL dump files with UTF-8 encoding
- Creates separate CSV files for each table
- Preserves column names
- Supports quoted and NULL values