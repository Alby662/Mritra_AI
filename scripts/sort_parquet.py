import duckdb


def main():
    print("Sorting trans.parquet with DuckDB...")
    duckdb.execute("PRAGMA threads=4")
    duckdb.execute("PRAGMA memory_limit='10GB'")

    query = """
    COPY (
        SELECT * FROM read_parquet('data/parquet/trans.parquet')
        ORDER BY ts ASC, row_id ASC
    ) TO 'data/parquet/trans_sorted.parquet' (FORMAT PARQUET);
    """
    duckdb.execute(query)
    print("Done!")


if __name__ == "__main__":
    main()
