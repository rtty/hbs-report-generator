#!bash
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macos
    YESTERDAY=$(date -v -1d '+%Y-%d-%m')
else
    # linux
    YESTERDAY=$(date -d 'yesterday' '+%Y-%d-%m')
fi
OUTPUT_DIR="reports"
OUTPUT_FILE="$OUTPUT_DIR/daily_report_$YESTERDAY.html"
[[ -d "$OUTPUT_DIR" ]] || mkdir -p "$OUTPUT_DIR"
python generator.py > "$OUTPUT_FILE"

