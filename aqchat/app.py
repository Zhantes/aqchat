import streamlit as st
import auth
import chat
import settings

pages = [
    st.Page(chat.page_chat, title="Chat"),
    st.Page(settings.page_settings, title="Settings"),
    st.Page(auth.page_login, title="PIN Login"),
]

pg = st.navigation(pages)
pg.run()
