import io
import streamlit as st
from streamlit_monaco_yaml import monaco_editor
from streamlit_searchbox import st_searchbox
# from streamlit_monaco import st_monaco
from openhems.modules.util import (
	ConfigurationManager, ConfigurationException, CastUtililty, CastException, ProjectConfiguration
)
import re
import json
from pathlib import Path
import yaml
import jsonschema
import dataclasses
from openhems.modules.web.unix_socket import UnixSocketServer

ROOT_PATH = Path(__file__).parents[5]

@dataclasses.dataclass
class BasicDeviceConfiguration:
    name: str
    type: str
    power_on_id: str
    power_id: str
    max_power: int
    strategy: str

@dataclasses.dataclass
class BasicConfiguration:
    solar: dict = None
    battery: dict = None
    contract: dict = None
    devices: list[BasicDeviceConfiguration] = dataclasses.field(default_factory=list)
    current_device_index: int = None

    def __json__(self):
        print("BasicConfiguration.__json__()", dataclasses.asdict(self))
        return dataclasses.asdict(self)

def load_config(config_page):
    with open(config_page, "r") as f:
        return yaml.safe_load(f)

def load_schema():
    with open(str(ROOT_PATH / "config/openhems.schema.yaml"), "r") as f:
        return yaml.safe_load(f)

def validate_config(config:dict|str, schema=None):
    if schema is None:
        schema  = load_schema()
    if isinstance(config, str):
        config = yaml.safe_load(config)
    jsonschema.validate(config, schema)
    return True

def save_config(config: dict|str, config_page: str, schema=None):
    validate_config(config, schema)
    with open(config_page, "w") as f:
        if isinstance(config, str):
            f.write(config)
        else:
            yaml.dump(config, f)
        return True

def snake_case(s):
  return '-'.join(
    re.sub(r"(\s|_|-)+"," ",
    re.sub(r"[A-Z]{2,}(?=[A-Z][a-z]+[0-9]*|\b)|[A-Z]?[a-z]+[0-9]*|[A-Z]|[0-9]+",
    lambda mo: ' ' + mo.group(0).lower(), s)).split())

def save_basic_config(basic_config: BasicConfiguration, config_page=ROOT_PATH / "config/openhems.yaml"):
    current_config = load_config(config_page)
    new_config = current_config.copy()
    # For now, we consider current_nodes=[] because, it's condition to display the basic configuration page,
    #  but in the future we could merge with existing nodes
    current_nodes = current_config.get("network", {}).get("nodes", [])
    for device in basic_config.devices:
        print("Device: ", device)
        new_node = {
            "id": device.get("name").lower(),
            "name": snake_case(device.get("name")),
            "strategy": device.get("strategy"),
            "class": "switch",
            "isOn": device.get("is_on"),
            "currentPower": device.get("current_power"),
            "maxPower": device.get("max_power")
        }
        new_config["network"]["nodes"].append(new_node)
    save_config(new_config, config_page)
    return True

@st.cache_data(ttl=3600)
def get_ha_entities() -> list:
    """ Get Home-Assistant entities list via UnixSocketServer."""
    return UnixSocketServer.list_components()

def select_ha_entity(search_term: str) -> list:
    """Fonction de recherche passée à st_searchbox."""
    if not search_term:
        return []  # Pas de suggestions tant que l'utilisateur n'a pas tapé
    all_entities = get_ha_entities()
    return [e for e in all_entities if search_term.lower() in e.lower()]

def st_select_from_dict(name:str, possibilities:dict, value=None):
    values = list(possibilities.keys())
    value = st.selectbox(
        name,
        options=values,
        format_func=lambda key: possibilities[key],
        index=0 if value is None or value not in values else values.index(value)
    )
    return value

def basic_configure_devices():
    steps = st.session_state.steps
    devices = st.session_state.config.devices
    if steps.substep == 0:
        st.subheader("📋 Appareils pilotables configurés")
        if devices:
            for i, d in enumerate(devices):
                cols = st.columns([3, 1, 1])
                cols[0].write(f"**{d['name']}** (type: {d['type']})")
                if cols[1].button("✏️", key=f"edit_{i}"):
                    st.session_state.config.current_device_index = i
                    st.session_state.steps.substep = 1
                    st.rerun()
                if cols[2].button("🗑️", key=f"del_{i}"):
                    devices.pop(i)
                    st.session_state.config.devices = devices
                    st.rerun()
        else:
            st.info("Aucun appareil configuré.")
        
        if st.button("➕ Ajouter un appareil"):
            st.session_state.config.current_device_index = None  # nouveau
            st.session_state.steps.substep = 1
            st.rerun()
        
        basic_configure_next_buttons()
    
    # Sous-étape 1 : configuration d'un appareil (nouveau ou édition)
    elif steps.substep == 1:
        st.subheader("⚙️ Configuration de l'appareil")
        
        # Récupérer l'appareil en cours (si édition)
        device = {
            "current_power": "",
            "is_on": "",
            "max_power": 2000,
            "min_power": 0,
            "min_duration": 0,
            "strategy": ""
        }
        if st.session_state.config.current_device_index is not None:
            device = devices[st.session_state.config.current_device_index]
        
        with st.form(key="device_form"):
            name = st.text_input("Nom de l'appareil", value=device.get("name", "") if device else "")
            device_type = st.selectbox(
                "Type d'appareil",
                ["Chauffe-eau", "Véhicule électrique", "Lave-linge", "Lave-vaisselle", "Climatiseur", "Autre"],
                index=0
            )
            # current_power = st_searchbox(
            #     search_function=select_ha_entity,
            #     placeholder="Rechercher une entité Home Assistant...",
            #     label="Entité de puissance",
            #     clear_on_submit=True,
            #     key="current_power",
            #     help="C'est l'id Home-Assistant qui permet de récupérer la puissance instantanée de l'appareil."
            # )
            ha_entities = [""] + get_ha_entities()
            val = device.get("current_power", "")
            current_power = st.selectbox(
                "Puissance instantanée (entité Home Assistant)",
                key="current_power",
                options=ha_entities,
                index=ha_entities.index(val) if val in ha_entities else 0,
                help="C'est l'id Home-Assistant qui permet de récupérer la puissance instantanée de l'appareil.",
            )
            val = device.get("is_on", "")
            is_on = st.selectbox(
                "Commande ON/OFF (entité Home Assistant)",
                key="is_on",
                options=ha_entities,
                index=ha_entities.index(val) if val in ha_entities else 0,
                help="C'est l'id Home-Assistant qui permet de piloter l'appareil.",
            )
            max_power = st.number_input("Puissance maximale (W)", min_value=0, step=100, 
                                        value=device.get("max_power", 2000))
            min_power = st.number_input("Puissance minimale (W)", min_value=0, step=100,
                                        value=device.get("min_power", 0))
            min_duration = st.number_input("Durée minimale de fonctionnement (min)", min_value=0, step=5,
                                           value=device.get("min_duration", 0))
            possible_strategy = {}
            if st.session_state.config.contract is None:
                possible_strategy["offgrid"] = ""
            else:
                possible_strategy["offgrid"] = "Ne pas utiliser le réseau public d'électricité (ou qu'en secours)"
                if st.session_state.config.contract in ["Heures Creuses", "Tempo EDF"]:
                    possible_strategy["offpeak"] = "Privilégier les heures creuses"
            if st.session_state.config.solar is not None:
                possible_strategy["emhass"] = "Optimiser le coût (en fonction du prix du kWh)"
            if st.session_state.config.battery is not None:
                possible_strategy["battery"] = "Optimiser l'utilisation de la batterie"
            strategy = st_select_from_dict(
                "Stratégie de gestion",
                possible_strategy,
                device.get("strategy", "")
            )
            
            submitted = st.form_submit_button("💾 Enregistrer")
        
        if submitted:
            new_device = {
                "name": name,
                "type": device_type,
                "current_power": current_power,
                "is_on": is_on,
                "max_power": max_power,
                "min_power": min_power,
                "min_duration": min_duration,
                "strategy": strategy,
            }
            if st.session_state.config.current_device_index is not None:
                # Modification
                # print("Update device config:", new_device)
                devices[st.session_state.config.current_device_index] = new_device
                st.session_state.config.current_device_index = None
            else:
                # Ajout
                # print("Add device config:", new_device)
                devices.append(new_device)
            st.session_state.config.devices = devices
            st.session_state.steps.substep = 0  # retour à la liste
            st.rerun()
        
        if st.button("❌ Annuler"):
            st.session_state.steps.substep = 0
            st.rerun()

step_list = [
    "Bienvenue",
    "Panneaux solaires",
    "Batterie",
    "Contrat électrique",
    "Appareils pilotables",
    "Récapitulatif"
]
class ConfigureSteps:
    step: int = 0
    substep: int = 0
    steps = [1]*len(step_list) # List nb substeps in each steps (1 by default)

    def get_total_steps(self):
        nb_steps = 0
        cur_step = 0
        for i in range(len(step_list)):
            n = self.steps[i]
            nb_steps += n
            if i < self.step:
                cur_step += n
            elif self.step == i:
                cur_step += self.substep
        return cur_step, nb_steps
            

    def decr_step(self, sub=False):
        if sub:
            self.substep -= 1
            if self.substep < 0:
                self.substep = 0
                self.decr_step()
        else:
            self.steps[self.step] = 1
            self.step -= 1
            self.substep = 0

    def incr_step(self, sub=False):
        if sub:
            self.substep += 1
            if self.substep >= self.steps[self.step]:
                self.substep = 0
                self.incr_step()
        else:
            self.step += 1
            self.steps[self.step] = 1
            self.substep = 0
    
    def set_nb_substeps(self, nb):
        self.steps[self.step] = nb
        self.substep = 0

def basic_configure_next_buttons(sub=False):
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅️ Précédent"):
            st.session_state.steps.decr_step(sub=sub)
            st.rerun()
    with col2:
        if st.button("Suivant ➡️"):
            st.session_state.steps.incr_step(sub=sub)
            st.rerun()
    

def basic_configure(config_page):
    # Initialization
    if "steps" not in st.session_state:
        st.session_state.config = BasicConfiguration()
        st.session_state.steps = ConfigureSteps()
    # Define the steps of the configuration process
    steps = st.session_state.steps
    # Display progress
    cur, nb = st.session_state.steps.get_total_steps()
    st.progress(cur / nb)
    st.title(f"⚙️ Assistant de configuration")
    st.header(f"{step_list[steps.step]} - ({cur} / {nb})")

    if steps.step == 0:
        st.markdown("""
        Cet assistant va vous aider à configurer OpenHEMS pour optimiser votre consommation électrique.
        Vous pourrez ensuite modifier les paramètres finement dans l'interface standard.
        """)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🚀 Commencer", use_container_width=True):
                st.session_state.steps.incr_step()
                st.rerun()
        with col2:
            if st.button("❌ Annuler", use_container_width=True):
                st.stop()

    elif steps.step == 1:
        st.write("**Avez-vous des panneaux solaires photovoltaïques ?**")
        choix = st.radio("Type de contrat", ("Non", "Oui, sans revente", "Oui, avec revente"), index=0, horizontal=True)
        if choix != "Non":
            puissance = st.number_input("Puissance crête installée (kWc)", min_value=0.5, step=0.5)
            st.session_state.config.solar = {"present": True, "sell": "revente" in choix, "peak_power": puissance}
        else:
            st.session_state.config.solar = None
        
        basic_configure_next_buttons()

    elif steps.step == 2:
        st.write("**Possédez-vous une batterie domestique ?**")
        has_battery = st.checkbox("Oui")
        if has_battery:
            capacity = st.number_input("Capacité utile (kWh)", min_value=1.0, step=1.0)
            power = st.number_input("Puissance de charge/décharge max (kW)", min_value=1.0, step=0.5)
            st.session_state.config.battery = {"capacity": capacity, "max_power": power}
        else:
            st.session_state.config.battery = None
        
        basic_configure_next_buttons()

    elif steps.step == 3:
        st.write("**Quel est votre fournisseur d'électricité ?**")
        contracts = load_config("src/openhems/data/ennergy_supplier.yaml")
        suppliers_default_list = {
            "none": "Aucun",
            "custom": "Autre"
        }
        suppliers_list = {}
        for k,supplier in contracts.items():
            suppliers_list[k] = supplier.get("label", k.title())
        contract = st.session_state.config.contract
        if contract is None:
            supplier_label = "none"
            contract = {}
        else:
            supplier_label = contract.get("supplier")
            if supplier_label not in suppliers_list:
                supplier_label = "custom"
        suppliers_default_list.update(suppliers_list)
        supplier_key = st_select_from_dict(
            "Fournisseur d'énergie",
            suppliers_default_list,
            value = supplier_label
        )
        if supplier_key=="none":
                st.session_state.config.contract = None
        else:
            if supplier == "custom":
                supplier = st.text_input(
                    "Fournisseur d'énergie",
                )
                contract_id = st.text_input(
                    "Nom du contrat"
                )
                st.session_state.config.contract = {
                    "supplier": supplier,
                    "name": contract_id
                }
            elif supplier_key in suppliers_list:
                supplier = contracts.get(supplier_key)
                contracts_list = {}
                for k,contract in supplier.get("contracts").items():
                    contracts_list[k] = contract.get("label", k.title())
                contract_id = st_select_from_dict(
                    "Nom du contrat",
                    contracts_list,
                    contract.get("name")
                )
                if contract_id:
                    details = supplier.get("contracts").get(contract_id)
                    details.update({
                        "supplier":supplier_key,
                        "supplier_label":supplier.get("label"),
                        "id":contract_id
                    })
                    contract.update(details)
            contracts_labels = {
                "price": "Prix du Kwh",
                "offpeak": "Heures-Creuses",
                "offpeak_price": "Prix du Kwh en Heures-Creuses",
                "duration": "Durée du contrat",
                "green": "Origine écologique",
                "surcharge": "Surcoût par rapport au prix de base",
                "discount": "Rabaix",
                "price_fix": "Durée de validité du prix",
                "comment": "Commentaires",
                "engagement": "Engagement",
            }
            for k,value in contract.items():
                if k not in ["id", "label", "supplier", "supplier_label"]:
                    label = contracts_labels.get(k, k.title())
                    ok = False
                    if not isinstance(value, str):
                        if isinstance(value, int):
                            new_value = st.number_input(label, value=value)
                            ok = True
                        else:
                            value = json.dumps(value)
                    if not ok:
                        new_value = st.text_input(label, value=value)
                    if new_value:
                        contract[k] = new_value
            if contract.get("id") == "none":
                contract = None
            st.session_state.config.contract = contract
        basic_configure_next_buttons()

    elif steps.step == 4:
        basic_configure_devices()

    elif steps.step == 5:
        st.subheader("Récapitulatif de votre configuration")
        st.json(json.dumps(st.session_state.config))
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ Modifier"):
                st.session_state.steps.decr_step()
                st.rerun()
        with col2:
            if st.button("✅ Générer la configuration OpenHEMS"):
                # Ici vous écrivez le fichier YAML final ou appelez l'API
                save_basic_config(st.session_state.config, config_page)
                st.success("Configuration sauvegardée ! Redémarrage d'OpenHEMS...")
                # Option : appeler un endpoint pour recharger la config
                st.balloons()
                st.session_state.steps = ConfigureSteps()  # reset steps
                st.rerun()

def yaml_editor_page(config_page):
    # Affichage de l'éditeur YAML
    st.title("✍️ Éditeur YAML Avancé")
    json_schema = load_schema()
    with open(config_page, "r") as f1:
        initial_text = f1.read()
        # st.write(f"ddd{initial_text}.")
        monaco_return = monaco_editor(
            initial_text,
            schema=json_schema,
            height=500,
            # a unique key avoids to reload the editor each time the content changed
            key=f"monaco_editor",
        )
        if monaco_return is not None:
            yaml_content = monaco_return.get('text')
        else:
            yaml_content = initial_text # Force generate error
        try:
            validate_config(config=yaml_content, schema=json_schema)
            st.success("✅ Fichier YAML valide !")
            if st.button("💾 Sauvegarder"):
                save_config(config=yaml_content, config_page=config_page, schema=json_schema)
                st.success("✅ Fichier YAML sauvegardé !")
                # print("Contenu sauvegardé :", yaml_content)
        except (jsonschema.exceptions.ValidationError, jsonschema.exceptions.SchemaError) as e:
            st.error(f"❌ Fichier YAML invalide selon le schéma JSON. : {e}")


config_page = str(ROOT_PATH / "config/openhems.yaml")
with open(config_page, "r") as f1:
    conf = yaml.safe_load(f1)
    if len(conf.get("network", {}).get("nodes", [])) == 0:
        basic_configure(config_page)
    else:
        yaml_editor_page(config_page)

