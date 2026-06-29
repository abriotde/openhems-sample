#pylint: disable=invalid-name
"""
Page to see a timeline of passed/futur actions
"""

import json
# pylint: disable=import-error
import streamlit as st
from streamlit_timeline import timeline

def timeline_page():
    """
    Page to see a timeline of passed/futur actions
    """
    # Use wide layout for better visualization
    st.set_page_config(page_title="Timeline", layout="wide")

    # Load your timeline data (from a JSON file or a dict)
    with open('timeline_data.json', 'r', encoding="utf-8") as f:
        data = json.load(f)

    # Render the timeline
    data['options'] = {'initial_zoom':0}
    timeline(data, height=400)

timeline_page()
