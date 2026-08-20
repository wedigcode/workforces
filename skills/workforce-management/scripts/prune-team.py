#!/usr/bin/env python3
"""
CLI wrapper for prune_team.py
Usage: python3 skills/workforce-management/scripts/prune-team.py <team-name> [options]
"""
import sys
import os

# Add current script directory to module search path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prune_team import main

if __name__ == "__main__":
    main()
