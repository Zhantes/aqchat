import os
from pathlib import Path
import streamlit as st

@st.cache_resource
def get_passcode_pin() -> str:
    pin_file = os.environ.get('PASSCODE_PIN_FILE', "/run/secrets/passcode_pin")

    try:
        passcode_pin = Path(pin_file).read_text('utf-8')
        print("[auth] Passcode configured.")
    except:
        passcode_pin = '123'
        print("[auth] WARNING: PIN file not found. Running with insecure passcode.")
    
    return passcode_pin.rstrip()

def has_authorized() -> bool:
    session_pin = st.session_state.get("auth_pin", None)
    return session_pin == get_passcode_pin()

def page_login():
    st.title("Enter PIN")

    if has_authorized():
        st.success("You are already logged in.")
        st.rerun()
        return

    with st.form(key="pin_form"):
        user_pin = st.text_input("PIN Code", type="password")
        login = st.form_submit_button("Login")
        if login:
            st.session_state["auth_pin"] = user_pin
            
            if has_authorized():
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Incorrect PIN.")

def logout():
    st.session_state["auth_pin"] = None
    st.rerun()