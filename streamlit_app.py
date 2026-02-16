import streamlit as st
from datamanager import SupaBaseDataManager

dm = SupaBaseDataManager()

st.title("Ár összehasonlító")

keyword = st.text_input("Keresőszó")

if keyword:
    own_df, raw_df = dm.get_products_by_keyword(keyword)

    st.subheader("Saját termékek")
    st.dataframe(own_df)

    st.subheader("Beszállítók")
    st.dataframe(raw_df)


