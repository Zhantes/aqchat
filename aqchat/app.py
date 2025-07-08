import streamlit as st
import auth
import chat
import settings
from dotenv import load_dotenv


login_page = [st.Page(auth.page_login, title="PIN Login")]

pages = [
    st.Page(chat.page_chat, title="Chat"),
    st.Page(settings.settings_main, title="Settings"),
    st.Page(auth.logout, title="Logout")
]

if auth.has_authorized():
    pg = st.navigation(pages)
else:
    pg = st.navigation(login_page)
load_dotenv()
pg.run()
