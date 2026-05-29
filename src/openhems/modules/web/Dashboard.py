"""
Dashboard web page to see and manage schedule of devices in OpenHEMS.
"""
#pylint: disable=invalid-name

import sys
from pathlib import Path
import dataclasses
import logging
from datetime import datetime
import streamlit as st # pylint: disable=E0401
import pandas as pd

# pylint: disable=wrong-import-position
ROOT_PATH = Path(__file__).parents[3]
sys.path.append(str(ROOT_PATH))
# from openhems.modules.network import OpenHEMSSchedule
from openhems.modules.network.homestate_updater import HomeStateUpdater
from openhems.modules.web.web_streamlit import OpenhemsHTTPServer
from openhems.modules.util import (
 	ConfigurationManager
)
from openhems.modules.web.driver_vpn import (
	VpnDriver
)

@dataclasses.dataclass
class OpenHEMSContext:
    """
    OpenHEMS context used in common with web server and core process
    """
    schedule: dict
    logger: logging.Logger
    configurator: ConfigurationManager
    translations: dict
    vpnDriver: VpnDriver
    network: HomeStateUpdater = None

def schedules_dict2dataframe(schedule):
    """
    Convert schedule dict to a pandas DataFrame for display in Streamlit
    """
    data = []
    for node_id, node in schedule.items():
        timeout = node.get("timeout_dt", None)
        if timeout is not None:
            timeout = datetime.strptime(timeout, "%Y-%m-%d %H:%M")
        row = {
            "ID": node_id,
            "Name": node.get("name", ""),
            "Duration": node.get("duration", 0),
            "Timeout": timeout
        }
        data.append(row)
    df = pd.DataFrame(data)
    return df

def update_schedule_from_dataframe(schedules, edited_df):
    """
    Update the schedule dict based on the edited DataFrame from Streamlit
    """
    updated = False
    schedule_keys = list(schedules.keys())
    for i, row in edited_df.iterrows():
        if i < len(schedule_keys):
            # print("Row:", row)
            node_id = schedule_keys[i]
            duration = row.get("Duration")
            if duration == 0:
                duration = None
            timeout = row.get("Timeout")
            if not pd.notna(timeout):
                # st.info(f"No timeout provided for node_id: {node_id}, {timeout}")
                timeout = None
            elif isinstance(timeout, datetime):
                # print("Convert timeout to string:", timeout)
                timeout = timeout.strftime("%Y-%m-%d %H:%M")
            # else:
            #     st.info(f"Timeout provided for node_id: {node_id}: ·{timeout}·")
            schedule = schedules.get(node_id)
            duration_orig = schedule.get("duration")
            timeout_orig = schedule.get("timeout_dt")
            # print(f"Original schedule for node_id {node_id}:
            #   duration={duration_orig}/{duration},
            #   timeout={timeout_orig}/{timeout}",
            #   file=sys.stderr)
            if duration_orig != duration or timeout_orig != timeout:
                OpenhemsHTTPServer.get_socket_client()\
                    .update_schedule(node_id, duration, timeout)
                updated = True
        # else:
        #     st.info(f"node_id: {i} / {schedule_keys}")
    return updated

def manage_schedules_page(mode=0):
    """
    Generate dashboard page  (to see & manage schedule)
    """
    if mode==0:
        st.title("Gestion des programmations")
    # Get schedules from the UnixSocketServer (core server)
    schedules = OpenhemsHTTPServer.get_socket_client().get_schedule()
    # print("DEBUG schedule:", schedules, file=sys.stderr)
    if schedules is None:
        st.warning("Erreur lors de la récupération des appareils programmables.")
        return

    # Create a DataFrame for display and editing
    # print("manage_schedules_page() : version =", st.version.STREAMLIT_VERSION_STRING,
    #   file=sys.stderr)
    df = schedules_dict2dataframe(schedules)
    # print("DataFrame for schedule:\n", df, file=sys.stderr)

    # Editable
    edited_df = st.data_editor(
        df,
        key="schedules_editor",
        hide_index=True,
        column_config={
            # "ID": st.column_config.TextColumn("ID", disabled=True),
            "Name": st.column_config.TextColumn("Name", disabled=True),
            "Duration": st.column_config.NumberColumn(
                "Duration",
                min_value=0,
                step=1,
                help="Durée en seconde durant laquelle vous souhaitez que l'appareil fonctionne."
            ),
            "Timeout": st.column_config.DatetimeColumn(
                "Timeout",
                help="Date à laquelle l'appareil devrait avoir terminé de fonctionner (optionnel)."
                # format="YYYY-MM-DD HH:mm",
                # default=datetime.now()
            )
        },
        # num_rows="dynamic"  # permet d'ajouter/supprimer des lignes si besoin
    )
    # print("data_editor set : ", edited_df, file=sys.stderr)

    # 0n save
    if st.button("💾 Appliquer les modifications"):
        # st.info(f"Button clicked")
        updated = update_schedule_from_dataframe(schedules, edited_df)
        if updated:
            st.success("Programmations mises à jour !")
        else:
            st.info("Aucune modification détectée.")
        # st.rerun()


# Configuration de la page

def main():
    """
    Entry point of the web application:
      manage if we display the wall or just the dashboard main tool
    """
    # print("main() called in streamlit_app.py")
    mode = int(st.query_params.get("n", "0"))
    if mode==1: # light mode
        st.markdown(
            """
            <style>
                /* Masquer la barre latérale */
                [data-testid="stSidebar"] {
                    display: none;
                }
                /* Masquer l'en-tête Streamlit */
                header {
                    display: none;
                }
                /* Optionnel : masquer le footer "Made with Streamlit" */
                footer {
                    display: none;
                }
                /* Ajuster la marge pour que le contenu prenne tout l'espace */
                .main > div {
                    padding-top: 0rem;
                }
            </style>
            """,
            unsafe_allow_html=True
        )
        # st.set_page_config(layout="wide")
    else:
        mode = 0
        st.sidebar.title("OpenHEMS")
        st.set_page_config(page_title="OpenHEMS", layout="wide")
        # st.sidebar.page_link("pages/01_Dashboard.py", label="Dashboard")
    manage_schedules_page(mode)

if __name__ == "__main__":
    main()
