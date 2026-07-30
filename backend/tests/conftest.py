import sys
from pathlib import Path

# 让 tests 可从 backend 根目录直接 import app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
