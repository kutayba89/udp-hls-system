"""
Compatibility wrapper.

The production configuration now lives in config_csv.py and streams.csv.
Importing from config.py still works for older scripts.
"""

from config_csv import *  # noqa: F401,F403

