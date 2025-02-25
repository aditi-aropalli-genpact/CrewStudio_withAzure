import streamlit as st
from streamlit import session_state as ss
import db_utils
from pg_agents import PageAgents
from pg_tasks import PageTasks
from pg_crews import PageCrews
from pg_tools import PageTools
from pg_crew_run import PageCrewRun
from pg_export_crew import PageExportCrew
from pg_results import PageResults
from dotenv import load_dotenv
import os
from urllib.parse import urlencode
# Okta
import streamlit as st
import requests
import os
from urllib.parse import urlencode, urlparse, parse_qs
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("OKTA_CLIENT_ID")
ISSUER = os.getenv("OKTA_ISSUER")
REDIRECT_URI = os.getenv("OKTA_REDIRECT_URI")
AUTHORIZATION_SERVER_ID = os.getenv("OKTA_AUTHORIZATION_SERVER_ID")
TOKEN_URL = f"{ISSUER}/oauth2/v1/token"
AUTH_URL = "https://genpact.oktapreview.com/oauth2/default/v1/authorize"

import hashlib
import base64
import secrets
from urllib.parse import urlencode

def generate_pkce_pair():
    code_verifier = secrets.token_urlsafe(64)  
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).decode().rstrip("=")  
    return code_verifier, code_challenge

# Ensure PKCE values are stored in session
if "code_verifier" not in ss:
    ss.code_verifier, ss.code_challenge = generate_pkce_pair()

def get_auth_url():
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "scope": "openid profile email",
        "redirect_uri": REDIRECT_URI,
        "state": "random_state_123",
        "nonce": "random_nonce_456",
        "code_challenge": ss.code_challenge,
        "code_challenge_method": "S256"
    }
    return f"{AUTH_URL}?{urlencode(params)}"


# Redirect to Okta for OAuth
def exchange_code_for_token(auth_code):
    TOKEN_URL = "https://genpact.oktapreview.com/oauth2/default/v1/token"

    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": "http://localhost:4200/home",  # Must match Okta settings
        "client_id": "0oa5vunv7xo0hZTuc0x7",
        "code_verifier": ss.code_verifier,  # Required for PKCE
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    print("🚀 Sending token request to Okta...")
    print("Request data:", data)

    response = requests.post(TOKEN_URL, data=data, headers=headers)

    print("🔄 Response status:", response.status_code)
    print("📜 Response body:", response.text)  # Check for error messages

    if response.status_code == 200:
        return response.json().get("access_token")
    
    return None



def authenticate():
    query_params = st.query_params
    auth_code = query_params.get("code", [None])[0]
    
    if auth_code and "access_token" not in st.session_state:
        access_token = exchange_code_for_token(auth_code)
        if access_token:
            st.session_state["access_token"] = access_token
            st.session_state["logged_in"] = True
            st.rerun()
        else:
            st.error("Authentication failed. Please try again.")
    
    if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
        st.write(f"[Click here to login with SSO]({get_auth_url()})")
        st.stop()
            
def pages():
    return {
        'Crews': PageCrews(),
        'Tools': PageTools(),
        'Agents': PageAgents(),
        'Tasks': PageTasks(),
        'Kickoff!': PageCrewRun(),
        'Results': PageResults(),
        'Import/export': PageExportCrew()
    }

def load_data():
    ss.agents = db_utils.load_agents()
    ss.tasks = db_utils.load_tasks()
    ss.crews = db_utils.load_crews()
    ss.tools = db_utils.load_tools()
    ss.enabled_tools = db_utils.load_tools_state()


def draw_sidebar():
    with st.sidebar:
        st.image("img/crewai_logo.png")

        if 'page' not in ss:
            ss.page = 'Crews'
        
        selected_page = st.radio('Page', list(pages().keys()), index=list(pages().keys()).index(ss.page),label_visibility="collapsed")
        if selected_page != ss.page:
            ss.page = selected_page
            st.rerun()
            
def main():
    st.set_page_config(page_title="CrewAI Studio", page_icon="img/favicon.ico", layout="wide")

    # Ensure Streamlit starts at /home
    if "path" not in st.query_params or st.query_params["path"] != "home":
        st.query_params["path"] = "home"  # Set the path to home
        st.rerun()   # Force reload to apply the change

    authenticate()
    st.set_page_config(page_title="CrewAI Studio", page_icon="img/favicon.ico", layout="wide")
    st.write("Welcome to CrewAI Studio! You are logged in.")
    st.set_page_config(page_title="CrewAI Studio", page_icon="img/favicon.ico", layout="wide")
    load_dotenv()
    if (str(os.getenv('AGENTOPS_ENABLED')).lower() in ['true', '1']) and not ss.get('agentops_failed', False):
        try:
            import agentops
            agentops.init(api_key=os.getenv('AGENTOPS_API_KEY'),auto_start_session=False)    
        except ModuleNotFoundError as e:
            ss.agentops_failed = True
            print(f"Error initializing AgentOps: {str(e)}")            
        
    db_utils.initialize_db()
    load_data()
    draw_sidebar()
    PageCrewRun.maintain_session_state() #this will persist the session state for the crew run page so crew run can be run in a separate thread
    pages()[ss.page].draw()
    
if __name__ == '__main__':
    main()
