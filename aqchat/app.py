import streamlit as st
import auth
import chat
import settings

login_page = [st.Page(auth.page_login, title="PIN Login")]

pages = [
    st.Page(chat.page_chat, title="Chat"),
    st.Page(settings.page_settings, title="Settings"),
    st.Page(auth.logout, title="Logout")
]

if auth.has_authorized():
    pg = st.navigation(pages)
else:
    pg = st.navigation(login_page)
pg.run()
