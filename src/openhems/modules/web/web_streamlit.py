"""
HTTP web server to give UI to configure OpenHEMS server:
* Set devices to schedule
* Switch on/offf VPN
*
"""
import sys
from pathlib import Path
import os
import signal
import time
import subprocess
import requests
import yaml
import streamlit as st

from openhems.unix_socket import UnixSocketClient # pylint: disable=E0401


# pylint: disable=wrong-import-position
ROOT_PATH = Path(__file__).parents[4]
sys.path.append(str(ROOT_PATH / "src"))
from openhems.modules.util import (
 	ConfigurationManager
)
from openhems.modules.web.driver_vpn import (
	VpnDriverIncronClient, VpnDriverWireguard
)

class OpenhemsHTTPServer():
    """
    Class for HTTP Server for OpenHEMS UI configuration
    """
    SESSION_FILE_PATH = ROOT_PATH / "src/openhems/data/streamlit_session.yaml"
    def __init__(self, logger, schedule, warning_messages, *,
            port=8000, html_root="/", in_docker=False, configurator=None):
        del html_root
        # print("Init OpenhemsHTTPServer2 with port ", port)
        self.logger = logger
        self.schedule = schedule
        self.warning_messages = warning_messages
        self.port = port
        # self.html_root = html_root
        if configurator is None:
            configurator = ConfigurationManager(self.logger)
        if isinstance(configurator, str):
            self.yaml_config_file_path = configurator
            configurator.defaultPath = ConfigurationManager.DEFAULT_PATH
            configurator = ConfigurationManager(self.logger)
            configurator.addYamlConfig(Path(self.yaml_config_file_path))
        else:
            self.yaml_config_file_path = configurator.getLastYamlConfFilepath()
        self.default_config_file_path = configurator.defaultPath
        self.configurator = configurator
        lang = configurator.get("localization.language")
        self.translations = {}
        self.lang = lang
        if in_docker:
            vpn_driver = VpnDriverIncronClient(self.logger)
        else:
            vpn_driver = VpnDriverWireguard(self.logger)
        self.vpn_driver = vpn_driver
        self.vpn_driver.test_vpn()
        self.proc = None
        self.define_default_session()
        # self.generateTemplateYamlParams(lang) # TODO

    def run(self, test_mode=False):
        """
        Run the web server throw a subprocess (bash cmd)
        """
        st.title("OpenHEMS")
        print("Run on port ", self.port)
        streamlit_app_path = str(ROOT_PATH / "src/openhems/modules/web/Dashboard.py")
        cmd = [sys.executable, "-m", "streamlit",
            "run", "--server.port="+str(self.port),
            streamlit_app_path,
        ]
        if test_mode:
            cmd.append("--server.headless=true")
            cmd.append("--browser.gatherUsageStats=false")
            print("Test mode: ", cmd)
            self.proc = subprocess.Popen( # pylint: disable=consider-using-with, subprocess-popen-preexec-fn
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # Permet de tuer tout le groupe de processus
            )
        else:
            self.proc = subprocess.run(cmd, check=False)
        # try:
        #     import streamlit.web.bootstrap as bootstrap
        #     bootstrap.run(streamlit_app_path, True, [], {})
        #     print("Launched bootstrap.run() with ", streamlit_app_path)
        # except KeyboardInterrupt:
        #     pass

    def define_default_session(self):
        """
        Initialize Streamlit session state with necessary objects (like UnixSocketClient)
        """
        with open(self.SESSION_FILE_PATH, "w", encoding="utf-8") as session_file:
            yaml.dump({
                "socket_path": self.configurator.get("server.socketpath"),
                "lang": self.lang,
            }, session_file)

    @staticmethod
    def init_session():
        """
        Initialize Streamlit session state with necessary objects (like UnixSocketClient)
        """
        with open(OpenhemsHTTPServer.SESSION_FILE_PATH, "r", encoding="utf-8") as key_file:
            session_data = yaml.load(key_file, Loader=yaml.FullLoader)
            st.session_state.unix_socket_client = UnixSocketClient(
                socket_path=session_data.get("socket_path")
            )
            # It would be better to store in more global variable (avoid to reload it at each session initialization)
            #  but no matter as we should have only one user (or very few)
            st.session_state.lang = session_data.get("lang")

    @staticmethod
    def get_socket_client():
        """
        Get the UnixSocketClient from Streamlit session state.
        """
        if 'unix_socket_client' not in st.session_state:
            OpenhemsHTTPServer.init_session()
        return st.session_state.unix_socket_client

    def test(self, path="/"):
        """
        Test function to run Streamlit app without running the whole OpenHEMS application.
        """
        # print("OpenhemsHTTPServer.test()", file=sys.stderr)
        url = "http://localhost:" + str(self.port) + path
        for _ in range(30):  # timeout 30 secondes
            try:
                response = requests.get(url, timeout=10)
                # print("GET ", response.text, file=sys.stderr)
                if response.status_code == 200:
                    return response.text
            except requests.ConnectionError:
                pass
            time.sleep(1)
        else:
            # Si on sort de la boucle sans avoir réussi
            # print("Le serveur Streamlit n'a pas démarré", file=sys.stderr)
            self.proc.terminate()
            raise RuntimeError("Le serveur Streamlit n'a pas démarré")

        yield url

@st.cache_data
def load_translations(lang: str) -> dict:
    """Charge un fichier YAML une seule fois et le met en cache."""
    if lang not in ["en", "fr"]:
        lang = "en"
    file_path = ROOT_PATH / ("src/openhems/data/keys_"+lang+".yaml")
    with open(file_path, 'r') as f:
        translations = yaml.safe_load(f)
    return translations

def trad(key: str) -> str:
    """Translate a key into the current language."""
    if 'lang' not in st.session_state:
        OpenhemsHTTPServer.init_session()
    translations = load_translations(st.session_state.lang)
    translation = translations.get(key)
    if translation is None:
        translation = key.title().replace("_", " ")
    return translation
