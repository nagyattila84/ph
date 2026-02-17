import streamlit as st
from werkzeug.security import check_password_hash
from datamanager import SupaBaseDataManager
import plotly.express as px

users = st.secrets["users"]

# ============= SESSION INIT ===============
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""

# ================= LOGIN =================
def login_page():   
    st.title("Bejelentkezés")
    username = st.text_input("Felhasználónév")
    password = st.text_input("Jelszó", type="password")

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

# ================= PAGES =================
def page_dashboard():
    st.header("📊 Dashboard")
    st.write("Ez az első oldal")

def page_search():
    dm = SupaBaseDataManager()
    st.title("Ár összehasonlító")
    
    keyword = st.text_input("Keresőszó")
    
    if keyword:
        own_df, raw_df = dm.get_products_by_keyword(keyword)
    
        st.subheader("Saját termékek")
        st.dataframe(own_df)
    
        st.subheader("Beszállítók")
        st.dataframe(raw_df)

def page_visual():
    dm = SupaBaseDataManager()
    own_df, raw_df = dm.get_products_by_keyword(keyword)
    fig = px.strip(
        own_df,
        x="price",
        y="name",
        color="shop",
        orientation="h",
        hover_data=["webshop_id", "price4"],
    )
    
    fig.update_traces(jitter=0.3, marker=dict(size=10))
    
    fig.update_layout(
        height=600,
        showlegend=True,
        xaxis_title="Ár",
        yaxis_title=""
    )
    
    st.plotly_chart(fig, use_container_width=True)

def page_settings():
    st.header("⚙️ Beállítások")
    st.write("User:", st.session_state.username)
    
#============================================
#===============   MAIN APP   ===============
#============================================
if not st.session_state.logged_in:
    login_page()

else:
    st.sidebar.write(f"Bejelentkezve: {st.session_state.username}")

    if st.sidebar.button("Kijelentkezés"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

    page = st.sidebar.radio(
        "Menü",
        ["Dashboard", "Keresés", "Vizuál", "Beállítások"]
    )

    if page == "Dashboard":
        page_dashboard()

    elif page == "Keresés":
        page_search()

    elif page == "Vizuál":
        page_visual()

    elif page == "Beállítások":
        page_settings()















