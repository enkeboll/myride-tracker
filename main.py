import sys
import os

# Delegate execution to src/server/main.py
src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "src"))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from server.main import main

if __name__ == "__main__":
    main()
