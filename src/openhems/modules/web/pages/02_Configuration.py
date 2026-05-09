import io
import streamlit as st
from streamlit_monaco_yaml import monaco_editor
# from streamlit_monaco import st_monaco
from openhems.modules.util import (
	ConfigurationManager, ConfigurationException, CastUtililty, CastException, ProjectConfiguration
)
from pathlib import Path
import copy
import yaml
import jsonschema
ROOT_PATH = Path(__file__).parents[5]

def get_tooltips(lang="en"):
    """
    Get tooltips from configuration in right language and add default values.
    """
    st.session_state.context.logger.debug("get_tooltips(%s)", lang)
    tooltipPath = ROOT_PATH / ("src/openhems/data/openhems_tooltips_"+lang+".yaml")
    configurator = ConfigurationManager(st.session_state.context.logger, defaultPath=tooltipPath)
    tooltips = configurator.get("", deepSearch=True)
    defaultConfig = ConfigurationManager(st.session_state.context.defaultConfFilepath)
    tooltips2 = copy.deepcopy(tooltips)
    tooltipWithDefault = st.session_state.context.translations["web"].get("defaultTooltip")
    for key, tooltip in tooltips.items():
        # self.logger.debug("Tooltip: %s : %s", key, tooltip)
        defaultValue = defaultConfig.get(key)
        if defaultValue is not None and str(defaultValue)!="":
            localVars = locals()
            localVars["tooltip"] = tooltip # else tooltip seam not used by Python checker.
            value = tooltipWithDefault.format(**localVars)
            # self.logger.debug("Tooltip with default: %s : %s", key, value)
            tooltips2[key] = value
    return tooltips2

def panel_page():
    st.title("OpenHEMS - Tableau de bord")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Stratégie active", st.session_state.context.current_strategy)
    with col2:
        st.metric("État VPN", "🟢 Connecté" if st.session_state.context.vpnDriver.testVPN() else "🔴 Déconnecté")
    with col3:
        st.metric("Appareils pilotables", len(st.session_state.context.schedule))
    
    st.subheader("Appareils programmés")
    data = []
    for node_id, node in st.session_state.context.schedule.items():
        data.append({
            "ID": node_id,
            "Durée (s)": node.duration,
            "Timeout": node.timeout,
            "État": node.status
        })
    st.dataframe(data, use_container_width=True)

def params_page():
    st.title("Configuration OpenHEMS")
    configurator = st.session_state.context.configurator
    tooltips = get_tooltips()  # votre méthode getTooltips(lang)
    
    # Parcours des clés de configuration
    for key, tooltip in tooltips.items():
        current_val = configurator.get(key)
        # Déterminer le type de widget
        if key in ConfigurationManager.HOOKS:
            # Cas particulier: liste de noeuds/stratégies
            st.markdown(f"**{key.replace('.', ' → ')}** : {tooltip}")
            # Afficher la liste existante
            nodes = configurator.get(key, default=[])
            edited = st.data_editor(nodes, key=key, num_rows="dynamic")
            if edited != nodes:
                configurator.add(key, edited)
        else:
            # Champ standard
            new_val = st.text_input(
                label=key.replace('.', ' → '),
                value=str(current_val),
                help=tooltip,
                key=key
            )
            if new_val != str(current_val):
                configurator.add(key, new_val)
    
    if st.button("💾 Sauvegarder"):
        configurator.save(st.session_state.context.yamlConfFilepath)
        st.success("Configuration sauvegardée !")
        st.rerun()

def configuration_page(page):
    import streamlit as st
    import pandas as pd
    import yaml

    st.title("📋 Éditeur Tabulaire de Configuration")

    sample_data = {
        "device_name": ["Chauffe-eau", "Véhicule électrique"],
        "power_w": [2000, 7000],
        "priority": [1, 2],
    }
    df = pd.DataFrame(sample_data)

    edited_df = st.data_editor(df, num_rows="dynamic")

    if st.button("💾 Générer et Sauvegarder la Config YAML"):
        devices_list = edited_df.to_dict(orient="records")
        yaml_config = {"devices": devices_list}
        with open(page, "w") as f:
            yaml.dump(yaml_config, f, default_flow_style=False)
        st.success("✅ Configuration YAML générée et sauvegardée !")
        st.code(yaml.dump(yaml_config, default_flow_style=False), language="yaml")

def yaml_editor_page(page):
    # Affichage de l'éditeur YAML
    st.title("✍️ Éditeur YAML Avancé")
    with open(str(ROOT_PATH / "config/openhems.schema.yaml"), "r") as f0:
        json_schema = yaml.safe_load(f0)
        with open(page, "r") as f1:
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
                data = yaml.safe_load(yaml_content)  # Vérifie que le YAML est syntaxiquement correct
                if jsonschema.validate(data, json_schema) is None:
                    st.success("✅ Fichier YAML valide !")
                    if st.button("💾 Sauvegarder"):
                        with open(page, "w") as f:
                            f.write(yaml_content)
                        st.success("✅ Fichier YAML sauvegardé !")
                        print("Contenu sauvegardé :", yaml_content)
                else:
                    st.error("❌ Fichier YAML invalide selon le schéma JSON.")
            except (jsonschema.exceptions.ValidationError, jsonschema.exceptions.SchemaError) as e:
                st.error(f"❌ Erreur YAML : {yaml_content} : {e}")

yaml_editor_page(str(ROOT_PATH / "config/openhems.yaml"))
