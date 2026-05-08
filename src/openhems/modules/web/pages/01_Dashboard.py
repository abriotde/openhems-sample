import streamlit as st
import pandas as pd
from datetime import datetime
from openhems.modules.web.unix_socket import UnixSocketServer
import json

def manage_schedules_page():
    st.title("Gestion des programmations")
    
    # Récupération des devices depuis votre contexte (à adapter)
    schedule = UnixSocketServer.get_schedule()  # dict: id -> node
    
    # Construction d'un DataFrame pour l'affichage et l'édition
    print("manage_schedules_page() : schedule =", schedule)
    data = []
    for node_id, node in schedule.items():
        data.append({
            "ID": node_id,
            "Durée (secondes)": node.get("duration", 0),
            "Timeout": node.get("timeout", None),
            "Name": node.get("name", "")
        })
    df = pd.DataFrame(data)
    
    # Éditable : l'utilisateur modifie directement le tableau
    edited_df = st.data_editor(
        df,
        column_config={
            "ID": st.column_config.TextColumn("ID", disabled=True),
            "Durée (secondes)": st.column_config.NumberColumn("Durée", min_value=0, step=1),
            "Timeout (datetime)": st.column_config.DatetimeColumn("Timeout (optionnel)", format="DD/MM/YYYY HH:mm"),
            "Statut": st.column_config.TextColumn("Statut", disabled=True)
        },
        use_container_width=True,
        num_rows="dynamic"  # permet d'ajouter/supprimer des lignes si besoin
    )
    
    # Bouton de sauvegarde
    if st.button("💾 Appliquer les modifications"):
        # Parcourir les lignes modifiées et mettre à jour le schedule
        for idx, row in edited_df.iterrows():
            node_id = row["ID"]
            if node_id in schedule:
                duration = int(row["Durée (secondes)"]) if row["Durée (secondes)"] > 0 else None
                timeout = row["Timeout (datetime)"] if pd.notna(row["Timeout (datetime)"]) else None
                schedule[node_id].setSchedule(duration, timeout)
        st.success("Programmations mises à jour !")
        st.rerun()

manage_schedules_page()
