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
import threading
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
        streamlit_app_path = str(ROOT_PATH / "src/openhems/modules/web/streamlit_app.py")
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


# Configuration de la page

def main():
    print("main() called in streamlit_app.py")
    # st.title("OpenHEMS")
    st.set_page_config(page_title="OpenHEMS", layout="wide")
    # Initialisation de l'état de session (remplace les variables globales)
    if 'context' not in st.session_state:
        print("main() : Initialisation du contexte dans st.session_state")
    print("main() : ok")
    

if __name__ == "__main__":
    main()
