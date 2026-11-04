"""Example projects (presets) of designed aircraft.

They are stored in the projects database (data/projects/projects.sqlite3, table presets);
the code keeps no project data.
"""
from calculations.project_store import load_presets

AIRCRAFT_PRESETS = load_presets()
