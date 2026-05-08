import streamlit as st
from openhems.modules.util import ProjectConfiguration

def about_page():
    st.title("À propos d'OpenHEMS")
    conf = ProjectConfiguration()
    st.markdown(f"""
    **{conf.getName()}** version {conf.getVersion()}  
    Licence : {conf.getLicence()}  
    [Site web]({conf.getUrls()['Homepage']}) | [Documentation]({conf.getUrls()['Documentation']})
    """)

about_page()