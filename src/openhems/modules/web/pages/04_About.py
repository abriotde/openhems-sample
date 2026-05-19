"""
About page for OpenHEMS web interface:
* Display licence
* Thanks to contributors
* Links to documentation and website
"""
#pylint: disable=invalid-name

import streamlit as st # pylint: disable=E0401
from openhems.modules.util import ProjectConfiguration

def about_page():
    """
    Display the about page of OpenHEMS web interface.
    """
    st.title("À propos d'OpenHEMS")
    conf = ProjectConfiguration()
    st.markdown(f"""
    **{conf.getName()}** version {conf.getVersion()}
    Licence : {conf.getLicence()}
    [Site web]({conf.getUrls()['Homepage']}) | [Documentation]({conf.getUrls()['Documentation']})
    """)

about_page()
