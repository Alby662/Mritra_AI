import pyarrow as pa
import pyarrow.csv as pv
import pyarrow.parquet as pq
import pandas as pd
import numpy as np
import gc
from mritra.config import load_config, repo_path

def chunk_prepare():
    cfg = load_config()
    files, fmt = cfg["dataset"]["files"], cfg["dataset"]["timestamp_format"]
    raw_path = repo_path(cfg["paths"]["raw"]) / files["trans"]
    out_path = repo_path(cfg["paths"]["parquet"]) / "trans.parquet"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    print("Streaming CSV to collect timestamps...")
    convert_options = pv.ConvertOptions(include_columns=["Timestamp"])
    reader = pv.open_csv(raw_path, convert_options=convert_options)
    
    ts_list = []
    for batch in reader:
        df = batch.to_pandas()
        ts_series = pd.to_datetime(df["Timestamp"], format="%Y/%m/%d %H:%M", utc=True).astype("int64") // 10**9
        ts_list.append(ts_series.to_numpy())
    
    print("Concatenating timestamps...")
    ts_np = np.concatenate(ts_list)
    del ts_list
    gc.collect()
    
    print("Sorting to find split boundaries...")
    n = len(ts_np)
    order = np.argsort(ts_np, kind="stable")
    sorted_ts = ts_np[order]
    del ts_np, order
    gc.collect()
    
    train = cfg["split"]["train"]
    val = cfg["split"]["val"]
    
    max_ts = {}
    start = 0
    for name, frac_end in (("train", train), ("val", train + val)):
        cut = int(np.floor(n * frac_end))
        if cut > start:
            cut = int(np.searchsorted(sorted_ts, sorted_ts[cut - 1], side="right"))
        cut = max(cut, start)
        if cut > 0:
            max_ts[name] = sorted_ts[cut - 1]
        else:
            max_ts[name] = 0
        start = cut
        
    print(f"Max TS for train: {max_ts.get('train')}")
    print(f"Max TS for val: {max_ts.get('val')}")
    
    del sorted_ts
    gc.collect()
    
    print("Writing parquet in chunks...")
    reader = pv.open_csv(raw_path)
    writer = None
    row_offset = 0
    max_train = max_ts.get("train", 0)
    max_val = max_ts.get("val", 0)
    
    for i, batch in enumerate(reader):
        df = batch.to_pandas()
        ts_series = pd.to_datetime(df.iloc[:, 0], format="%Y/%m/%d %H:%M", utc=True).astype("int64") // 10**9
        split_col = np.where(ts_series <= max_train, "train", np.where(ts_series <= max_val, "val", "test"))
        
        # Manually overwrite columns to prevent duplicate 'Account' renaming issues
        df.columns = ["ts", "from_bank", "from_acct", "to_bank", "to_acct", "amt_recv", "cur_recv", "amt_paid", "cur_paid", "fmt", "is_laund"]
        df["ts"] = ts_series
        df["split"] = split_col
        df.insert(0, "row_id", range(row_offset, row_offset + len(df)))
        row_offset += len(df)
        
        table = pa.Table.from_pandas(df)
        if writer is None:
            writer = pq.ParquetWriter(out_path, table.schema)
        writer.write_table(table)
        
        if i % 10 == 0:
            print(f"Processed batch {i}, row_offset {row_offset}")
            
    writer.close()
    print(f"Done writing trans.parquet, total rows: {row_offset}")
    
    patterns_path = repo_path(cfg["paths"]["raw"]) / files["patterns"]
    if patterns_path.exists():
        print("Parsing patterns...")
        from mritra.data.patterns import parse_patterns
        patterns = parse_patterns(patterns_path, fmt)
        patterns.to_parquet(repo_path(cfg["paths"]["parquet"]) / "patterns.parquet", index=False)
        print("Done writing patterns.parquet")

if __name__ == "__main__":
    chunk_prepare()
