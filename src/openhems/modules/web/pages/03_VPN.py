"""
VPN control page for OpenHEMS web interface:
"""
#pylint: disable=invalid-name

import streamlit as st  # pylint: disable=E0401

def vpn_control():
    """
    Display the VPN control page.
    """
    st.subheader("Contrôle VPN")
    vpn = st.session_state.context.vpn_driver
    connected = vpn.test_vpn()
    if connected:
        st.success("VPN actif")
        if st.button("🔌 Déconnecter"):
            vpn.start_vpn(False)
            st.rerun()
    else:
        st.warning("VPN inactif")
        if st.button("🔒 Connecter"):
            vpn.start_vpn(True)
            st.rerun()

# Dans panel_page, après l'affichage du dataframe
# edited_df = st.data_editor(df, key="schedule_editor")
# if st.button("Appliquer les modifications"):
#     for _, row in edited_df.iterrows():
#         node_id = row["ID"]
#         node = st.session_state.context.schedule[node_id]
#         node.set_schedule(int(row["Durée (s)"]), row["Timeout"])
#     st.success("Planification mise à jour")
