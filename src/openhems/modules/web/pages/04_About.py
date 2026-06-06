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
    [Site web]({conf.getUrls().get('Homepage', '#')}) | [Documentation]({conf.getUrls().get('Documentation', '#')})
    [Source code]({conf.getUrls().get('Repository', '#')}) | [Bug tracker]({conf.getUrls().get('Issues', '#')})
    Contact : {conf.getContact()}

    N'hésitez pas à contribuer au projet sur [GitHub]({conf.getUrls().get('Source', '#')})
    """)
    # Merci à tous les contributeurs qui ont participé au développement d'OpenHEMS :

about_page()
