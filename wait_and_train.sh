echo "Waiting for build_features to finish..."
while pgrep -f "scripts/build_features.py" > /dev/null; do
  sleep 10
done
echo "build_features finished. Starting train_models..."
uv run python scripts/train_models.py --configs C1,C3,C4 --run-id 20261005T210833Z
