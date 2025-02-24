import streamlit as st
from streamlit import session_state as ss
from dotenv import load_dotenv

import os

#okta
from okta.client import Client as OktaClient
from okta.models.authorization_server import AuthorizationServer

org_url = os.environ.get("OKTA_ORG_URL")
client_id = os.environ.get("OKTA_CLIENT_ID")
redirect_uri = os.environ.get("OKTA_REDIRECT_URI")  # e.g., "http://localhost:8501/callback"
authorization_server_id = os.environ.get("OKTA_AUTHORIZATION_SERVER_ID")

config = {
    'orgUrl': org_url,
    'clientId': client_id,
    'authorizationServerId': authorization_server_id
}
okta_client = OktaClient(config)

if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "user_info" not in st.session_state:
    st.session_state.user_info = None

print(st.st.session_state.access_token)
print(st.session_state.user_info)