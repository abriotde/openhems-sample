import streamlit as st
import pandas as pd
from datetime import datetime
from openhems.modules.web.unix_socket import UnixSocketServer
import datetime

def manage_schedules_page():
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
            "ID": node_id,
            "Name": node.get("name", ""),
            "Duration": node.get("duration", 0),
            "Timeout": timeout
        }
        data.append(row)
    df = pd.DataFrame(data)
    
    # Editable
    edited_df = st.data_editor(
        df,
        column_config={
            "ID": st.column_config.TextColumn("ID", disabled=True),
            "Name": st.column_config.TextColumn("Name", disabled=True),
            "Duration": st.column_config.NumberColumn("Duration", min_value=0, step=1),
            "Timeout": st.column_config.DatetimeColumn("Timeout",
                format="YYYY-MM-DD HH:mm", 
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

manage_schedules_page()
