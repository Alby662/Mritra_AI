uv run python scripts/train_models.py --configs C1,C3 --run-id 20261005T210833Z &
pid=$!
while kill -0 $pid 2>/dev/null; do
  ps -o rss= -p $pid
  sleep 0.5
done
wait $pid
echo "Exit code: $?"
