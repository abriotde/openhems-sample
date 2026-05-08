import streamlit as st
from openhems.modules.util import (
	ConfigurationManager, ConfigurationException, CastUtililty, CastException, ProjectConfiguration
)
from pathlib import Path
import copy


ROOT_PATH = Path(__file__).parents[3]

def get_tooltips(lang="en"):
    """
    Get tooltips from configuration in right language and add default values.
    """
    st.session_state.context.logger.debug("get_tooltips(%s)", lang)
    tooltipPath = ROOT_PATH / ("data/openhems_tooltips_"+lang+".yaml")
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

