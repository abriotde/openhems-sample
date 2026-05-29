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
import streamlit as st #pylint: disable=import-error

from openhems.unix_socket_client import UnixSocketClient # pylint: disable=E0401
from openhems.modules.util import get_log_file_path # pylint: disable=E0401


# pylint: disable=wrong-import-position
ROOT_PATH = Path(__file__).parents[3]
sys.path.append(str(ROOT_PATH))
from openhems.modules.util import (
 	ConfigurationManager
)
from openhems.modules.web.driver_vpn import (
	VpnDriverIncronClient, VpnDriverWireguard
)
from openhems.modules.util import getLogger as OpenHEMSGetLogger

@st.cache_data
def get_http_configuration():
    """
    Get the YAML configuration file path.
    """
    with open(OpenhemsHTTPServer.SESSION_FILE_PATH, "r", encoding="utf-8") as key_file:
        session_data = yaml.load(key_file, Loader=yaml.FullLoader)
        return session_data
    return {}

@st.cache_data
def get_logger():
    """
    Get the logger for the web server.
    """
    # TODO : better to have a global logger for all the application (and not one per module)
    #  but it is not so easy to do with Streamlit caching system
    #  (and it is not a big deal as we should have only one user)
    logger = OpenHEMSGetLogger(
        loglevel="info",
        logformat="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        logfile=get_http_configuration().get("log_path", ""),
        inDocker=False
    )
    return logger

class OpenhemsHTTPServer():
    """
    Class for HTTP Server for OpenHEMS UI configuration
    """
    SESSION_FILE_PATH = ROOT_PATH / "openhems/data/streamlit_session.yaml"

    def __init__(self, logger, schedule, warning_messages, *,
            port=8000, html_root="/", in_docker=False, configurator:ConfigurationManager=None):
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
        self.configurator = configurator
        lang = configurator.get("localization.language")
        self.lang = lang
        if in_docker:
            self.vpn_driver = VpnDriverIncronClient(self.logger)
        else:
            self.vpn_driver = VpnDriverWireguard(self.logger)
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
        streamlit_app_path = str(ROOT_PATH / "openhems/modules/web/Dashboard.py")
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

    def stop(self):
        """
        Should be used to stop properly.
        """
        os.killpg(os.getpgid(self.proc.pid), signal.SIGTERM)

    def define_default_session(self):
        """
        Initialize Streamlit session state with necessary objects (like UnixSocketClient)
        """
        print("ROOT_PATH=",ROOT_PATH)
        with open(self.SESSION_FILE_PATH, "w", encoding="utf-8") as session_file:
            log_path = self.configurator.get("server.logfile")
            if log_path=="":
                log_path = get_log_file_path(self.logger)
            datas = {
                "socket_path": self.configurator.get("server.socketpath"),
                "lang": self.lang,
                "log_path": log_path,
                "conf_path": str(self.configurator.getLastYamlConfFilepath()),
            }
            yaml.dump(datas, session_file)
            self.logger.info(
                "Session file created at '" + str(self.SESSION_FILE_PATH) 
                + "' with data: " + str(datas)
            )

    @staticmethod
    def init_session():
        """
        Initialize Streamlit session state with necessary objects (like UnixSocketClient)
        """
        session_data = get_http_configuration()
        st.session_state.unix_socket_client = UnixSocketClient(
            socket_path=session_data.get("socket_path")
        )
        # It would be better to store in more global variable
        #  (avoid to reload it at each session initialization)
        #  but no matter as we should have only one user (or very few)
        st.session_state.lang = session_data.get("lang")
        st.session_state.configurator_path = session_data.get("conf_path")

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
        # Si on sort de la boucle sans avoir réussi
        # print("Le serveur Streamlit n'a pas démarré", file=sys.stderr)
        self.proc.terminate()
        raise RuntimeError("Le serveur Streamlit n'a pas démarré")
        # yield url

@st.cache_data
def load_translations(lang: str) -> dict:
    """Charge un fichier YAML une seule fois et le met en cache."""
    if lang not in ["en", "fr"]:
        lang = "en"
    file_path = ROOT_PATH / ("src/openhems/data/keys_"+lang+".yaml")
    translations = {}
    with open(file_path, 'r', encoding='utf-8') as f:
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
