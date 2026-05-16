from attr import dataclass
import streamlit as st
import yaml
import sys
from pathlib import Path
from dataclasses import dataclass
import logging
ROOT_PATH = Path(__file__).parents[4]
sys.path.append(str(ROOT_PATH / "src"))
from openhems.modules.network.homestate_updater import HomeStateUpdater
from openhems.modules.util import (
 	ConfigurationManager
)
from driver_vpn import VpnDriverWireguard, VpnDriverIncronClient, VpnDriver
import sys
import subprocess

@dataclass
class OpenHEMSContext:
    lock: str
    schedule: dict
    logger: logging.Logger
    configurator: ConfigurationManager
    translations: dict
    vpnDriver: VpnDriver
    network: HomeStateUpdater = None


class OpenhemsHTTPServer2():
    """
    Class for HTTP Server for OpenHEMS UI configuration
    """
    def __init__(self, mylogger, schedule, warningMessages, *,
            port=8000, htmlRoot="/", inDocker=False, configurator=None):
        # print("Init OpenhemsHTTPServer2 with port ", port)
        self.logger = mylogger
        self.schedule = schedule
        self.warningMessages = warningMessages
        self.port = port
        self.htmlRoot = htmlRoot
        if configurator is None:
            configurator = ConfigurationManager(self.logger)
        if isinstance(configurator, str):
            self.yamlConfFilepath = configurator
            configurator.defaultPath = ConfigurationManager.DEFAULT_PATH
            configurator = ConfigurationManager(self.logger)
            configurator.addYamlConfig(Path(self.yamlConfFilepath))
        else:
            self.yamlConfFilepath = configurator.getLastYamlConfFilepath()
        self.defaultConfFilepath = configurator.defaultPath
        self.configurator = configurator
        lang = configurator.get("localization.language")
        self.translations = {}
        translationsPath = ROOT_PATH / ("src/openhems/data/keys_"+lang+".yaml")
        with translationsPath.open("r", encoding="utf-8") as keyFile:
            self.translations = yaml.load(keyFile, Loader=yaml.FullLoader)
        if inDocker:
            vpnDriver = VpnDriverIncronClient(mylogger)
        else:
            vpnDriver = VpnDriverWireguard(mylogger)
        self.vpnDriver = vpnDriver
        self.vpnDriver.testVPN()
        # self.generateTemplateYamlParams(lang) # TODO

    def run(self):
        st.title("OpenHEMS")
        print("Run on port ", self.port)
        streamlit_app_path = str(ROOT_PATH / "src/openhems/modules/web/Dashboard.py")
        subprocess.run([sys.executable, "-m", "streamlit",
            "run", "--server.port="+str(self.port),
            # "--server.headless=true",
            streamlit_app_path,
        ])
        # try:
        #     import streamlit.web.bootstrap as bootstrap
        #     bootstrap.run(streamlit_app_path, True, [], {})
        #     print("Launched bootstrap.run() with ", streamlit_app_path)
        # except KeyboardInterrupt:
        #     pass
import streamlit as st
import pandas as pd
from datetime import datetime
from openhems.modules.web.unix_socket import UnixSocketServer
import datetime

def manage_schedules_page(mode=0):
    if mode==0:
        st.title("Gestion des programmations")
    
    # Get schedules from the UnixSocketServer (core server)
    schedule = UnixSocketServer.get_schedule()
    # st.write("DEBUG schedule:", schedule)

    # Create a DataFrame for display and editing
    print("manage_schedules_page() : schedule =", schedule)
    data = []
    for node_id, node in schedule.items():
        timeout = node.get("timeout_dt", None)
        if timeout is not None:
            timeout = datetime.datetime.strptime(timeout, "%Y-%m-%d %H:%M")
        row = {
            # "ID": node_id,
            "Name": node.get("name", ""),
            "Duration": node.get("duration", 0),
            "Timeout": timeout
        }
        data.append(row)
    df = pd.DataFrame(data)
    
    # Editable
    edited_df = st.data_editor(
        df,
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
                # default=datetime.datetime.now()
            )
        },
        # num_rows="dynamic"  # permet d'ajouter/supprimer des lignes si besoin
    )
    
    # 0n save
    if st.button("💾 Appliquer les modifications"):
        for idx, row in edited_df.iterrows():
            node_id = row["ID"]
            if node_id in schedule:
                print("Row:", row)
                duration = row.get("Duration")
                if duration == 0: duration = None
                timeout = row.get("Timeout")
                if not pd.notna(timeout): timeout = None
                elif isinstance(timeout, datetime.datetime):
                    print("Convert timeout to string:", timeout)
                    timeout = timeout.strftime("%Y-%m-%dT%H:%M:%S")
                UnixSocketServer.update_schedule(node_id, duration, timeout)
        st.success("Programmations mises à jour !")
        st.rerun()


# Configuration de la page

def main():
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
