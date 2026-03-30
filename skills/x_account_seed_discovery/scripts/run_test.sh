#!/bin/bash
cd "$(dirname "$0")"
python3 search_sotwe.py --profile ~/.x-discovery/chrome-profile search --query "politics Indonesia" --max-results 10
