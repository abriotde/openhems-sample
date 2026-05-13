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

def load_config(config):
    pass

def basic_configure(page):
    # Initialization
    if "step" not in st.session_state:
        st.session_state.step = 0
        st.session_state.config = {}
    # Define the steps of the configuration process
    steps = [
        "Bienvenue",
        "Panneaux solaires",
        "Batterie",
        "Contrat électrique",
        "Appareils pilotables",
        "Récapitulatif"
    ]

    # Display progress
    st.progress((st.session_state.step) / (len(steps)-1))
    st.title(f"⚙️ Assistant de configuration OpenHEMS - {steps[st.session_state.step]}")

    if st.session_state.step == 0:
        st.markdown("""
        Cet assistant va vous aider à configurer OpenHEMS pour optimiser votre consommation électrique.
        Vous pourrez ensuite modifier les paramètres finement dans l'interface standard.
        """)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🚀 Commencer", use_container_width=True):
                st.session_state.step += 1
                st.rerun()
        with col2:
            if st.button("❌ Annuler", use_container_width=True):
                st.stop()

    elif st.session_state.step == 1:
        st.write("**Avez-vous des panneaux solaires photovoltaïques ?**")
        choix = st.radio("", ("Non", "Oui, sans revente", "Oui, avec revente"), index=0, horizontal=True)
        if choix != "Non":
            puissance = st.number_input("Puissance crête installée (kWc)", min_value=0.5, step=0.5)
            st.session_state.config["solar"] = {"present": True, "sell": "revente" in choix, "peak_power": puissance}
        else:
            st.session_state.config["solar"] = {"present": False}
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ Précédent"):
                st.session_state.step -= 1
                st.rerun()
        with col2:
            if st.button("Suivant ➡️"):
                st.session_state.step += 1
                st.rerun()

    elif st.session_state.step == 2:
        st.write("**Possédez-vous une batterie domestique ?**")
        has_battery = st.checkbox("Oui")
        if has_battery:
            capacity = st.number_input("Capacité utile (kWh)", min_value=1.0, step=1.0)
            power = st.number_input("Puissance de charge/décharge max (kW)", min_value=1.0, step=0.5)
            st.session_state.config["battery"] = {"capacity": capacity, "max_power": power}
        else:
            st.session_state.config["battery"] = None
        
        cols = st.columns(2)
        with cols[0]:
            if st.button("⬅️ Précédent"):
                st.session_state.step -= 1
                st.rerun()
        with cols[1]:
            if st.button("Suivant ➡️"):
                st.session_state.step += 1
                st.rerun()

    elif st.session_state.step == 3:
        st.write("**Quel est votre contrat d'électricité ?**")
        contrat = st.selectbox("Type", ["Base", "Heures Creuses", "Tempo EDF", "Zen Week-end", "Autre"])
        if contrat in ["Heures Creuses", "Tempo EDF", "Zen Week-end"]:
            # On peut demander les plages horaires, mais on peut aussi les laisser par défaut
            st.info("Les plages horaires seront automatiquement détectées via l'API RTE (pour Tempo) ou via l'intégration Home Assistant.")
        st.session_state.config["contract"] = contrat
        
        cols = st.columns(2)
        with cols[0]:
            if st.button("⬅️ Précédent"):
                st.session_state.step -= 1
                st.rerun()
        with cols[1]:
            if st.button("Suivant ➡️"):
                st.session_state.step += 1
                st.rerun()

    elif st.session_state.step == 4:
        st.write("**Quels appareils pilotables souhaitez-vous gérer ?**")
        appliances = ["Chauffe-eau", "Véhicule électrique", "Lave-linge", "Lave-vaisselle", "Climatiseur", "Autre"]
        selected = []
        for app in appliances:
            if st.checkbox(app):
                selected.append(app)
        st.session_state.config["controllable_devices"] = selected
        
        cols = st.columns(2)
        with cols[0]:
            if st.button("⬅️ Précédent"):
                st.session_state.step -= 1
                st.rerun()
        with cols[1]:
            if st.button("Suivant ➡️"):
                st.session_state.step += 1
                st.rerun()

    elif st.session_state.step == 5:
        st.subheader("Récapitulatif de votre configuration")
        st.json(st.session_state.config)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ Modifier"):
                st.session_state.step = max(0, st.session_state.step - 2)  # retour à l'étape précédente
                st.rerun()
        with col2:
            if st.button("✅ Générer la configuration OpenHEMS"):
                # Ici vous écrivez le fichier YAML final ou appelez l'API
                load_config(st.session_state.config)
                st.success("Configuration sauvegardée ! Redémarrage d'OpenHEMS...")
                # Option : appeler un endpoint pour recharger la config
                st.balloons()
                st.session_state.step = 0  # réinitialiser pour un prochain usage
                st.rerun()


def yaml_editor_page(page):
    del st.session_state.step

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


config_page = str(ROOT_PATH / "config/openhems.yaml")
with open(config_page, "r") as f1:
    conf = yaml.safe_load(f1)
    if len(conf.get("network", {}).get("nodes", [])) == 0:
        basic_configure(config_page)
    else:
        yaml_editor_page(config_page)

