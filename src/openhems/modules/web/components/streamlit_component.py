import pathlib

import pandas as pd
import streamlit as st
import base64

hello_component = st.components.v2.component(
    name="hello_world",
    html="<h2>Hello, World!</h2>",
    css="h2 { color: var(--st-primary-color); }",
)

PATH = pathlib.Path(__file__).parent.parent.resolve()

@st.cache_data
def load_file(path):
    """
    Load a file and return its content.
    """
    p = pathlib.Path(path)
    with p.open("r", encoding='utf-8') as file:
        return file.read()

@st.cache_data
def load_image(image_path):
    """
    Load an image file and return its content as HTML code.
    """
    p = pathlib.Path(image_path)
    print("load_image(", p.absolute(),")")
    if p.suffix.lower() in [".svg"]:
        with p.open("r", encoding='utf-8') as img_file:
            return img_file.read()
    elif p.suffix.lower() in [".png", ".jpg", ".jpeg"]:
        with p.open("rb") as img_file:
            base64_data = base64.b64encode(img_file.read()).decode("utf-8")
            return f"<img src='data:image/{p.suffix[1:]};base64,{base64_data}' />"
    return None



device_programm_component = st.components.v2.component(
    name="device_programm",
    html="""<div id="data-container">Loading data...</div>""",
    js=load_file(PATH / "js/streamlit_component.js"),
    css=load_file(PATH / "css/openhems.css"),
)

def get_device_programm_component(node, on_node_change=None):
    """
    Get the device programm component data.
    """
    if on_node_change is None:
        on_node_change = lambda: None
    component = device_programm_component(
        on_node_change=on_node_change,
        data={
            "node": node,
            "id": node.get("id", node.get("name", "id")),
            "translate": {
                "tooltip_duration": "Durée",
                "tooltip_timeout": "Timeout",
                "for": "Pendant",
                "before": "Fin avant"
            },
            "img": {
                "hourglass": load_image(PATH / "img/hourglass.svg"),
                "alarm": load_image(PATH / "img/alarm.svg")
            }
        }
    )
    return component
