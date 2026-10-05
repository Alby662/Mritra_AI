import os
import time

import pandas as pd

from scripts.build_features import _should_skip


def test_should_skip_logic(tmp_path):
    out_path = tmp_path / "test.parquet"

    # Create a dummy parquet file
    pd.DataFrame({"colA": [1]}).to_parquet(out_path)

    # Artificially push mtime to the future so it's newer than the source code
    now = time.time()
    os.utime(out_path, (now + 1000, now + 1000))

    # 1. Schema missing expected column (False)
    assert _should_skip(out_path, ["colA", "colB"]) is False

    # 2. Fresh, complete file (True)
    assert _should_skip(out_path, ["colA"]) is True

    # 3. Stale mtime (False)
    # Push mtime to the distant past (older than any code file)
    os.utime(out_path, (1000, 1000))
    assert _should_skip(out_path, ["colA"]) is False
