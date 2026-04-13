import sys
import os

# Make both packages importable from the test runner
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared-contracts-py"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
