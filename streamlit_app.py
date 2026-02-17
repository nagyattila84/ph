import streamlit as st
from werkzeug.security import check_password_hash
from werkzeug.security import *
from datamanager import SupaBaseDataManager

dm = SupaBaseDataManager()

if st.button("Belépés"):
    ok = False

    if username in users:
        try:
            ok = check_password_hash(users[username], password)
        except Exception as e:
            st.write(e)

    if ok:
        st.session_state["logged_in"] = True
        st.session_state["username"] = username
        st.rerun()
    else:
        st.error("Hibás felhasználónév vagy jelszó")

    
    # --- Itt lehet adatbázis lekérdezést csinálni ---
    st.title("Ár összehasonlító")
    
    keyword = st.text_input("Keresőszó")
    
    if keyword:
        own_df, raw_df = dm.get_products_by_keyword(keyword)
    
        st.subheader("Saját termékek")
        st.dataframe(own_df)
    
        st.subheader("Beszállítók")
        st.dataframe(raw_df)









