import os
import sys

TESTS_DIR = os.path.dirname(__file__)
PACKAGE_DIR = os.path.dirname(TESTS_DIR)

if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)

if PACKAGE_DIR not in sys.path:
    sys.path.insert(0, PACKAGE_DIR)
