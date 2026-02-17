import streamlit as st
from werkzeug.security import check_password_hash
from datamanager import SupaBaseDataManager

dm = SupaBaseDataManager()





# --- Secrets-ből olvasás ---
users = st.secrets["users"]

# --- Session state a bejelentkezéshez ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""

# --- Bejelentkezési űrlap ---
if not st.session_state["logged_in"]:
    st.title("Bejelentkezés")
    username = st.text_input("Felhasználónév")
    password = st.text_input("Jelszó", type="password")

    if st.button("Belépés"):
        if username in users and check_password_hash(users[username], password):
            st.success(f"Sikeres belépés: {username}")
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
        else:
            st.error("Hibás felhasználónév vagy jelszó")
else:
    st.sidebar.write(f"Bejelentkezve: {st.session_state['username']}")
    st.sidebar.button("Kijelentkezés", on_click=lambda: st.session_state.update({"logged_in": False, "username": ""}))
    
    # --- Itt lehet adatbázis lekérdezést csinálni ---
    st.title("Ár összehasonlító")
    
    keyword = st.text_input("Keresőszó")
    
    if keyword:
        own_df, raw_df = dm.get_products_by_keyword(keyword)
    
        st.subheader("Saját termékek")
        st.dataframe(own_df)
    
        st.subheader("Beszállítók")
        st.dataframe(raw_df)





