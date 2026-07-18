"""Make the ``amii_demo`` package importable when pytest runs from the repo
root (project tests run separately from the core gate). Adds this project
directory to ``sys.path`` so ``import amii_demo`` resolves without
installing the project.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
