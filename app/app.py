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
from llms import load_secrets_fron_env
import os

#okta
from okta.client import Client as OktaClient
from okta.models.authorization_server import AuthorizationServer

# org_url = os.environ.get("OKTA_ORG_URL")
# client_id = os.environ.get("OKTA_CLIENT_ID")
# redirect_uri = os.environ.get("OKTA_REDIRECT_URI")  # e.g., "http://localhost:8501/callback"
# authorization_server_id = os.environ.get("OKTA_AUTHORIZATION_SERVER_ID")

# config = {
#     'orgUrl': org_url,
#     'clientId': client_id,
#     'authorizationServerId': authorization_server_id
# }
# okta_client = OktaClient(config)

# if "access_token" not in st.session_state:
#     st.session_state.access_token = None
# if "user_info" not in st.session_state:
#     st.session_state.user_info = None

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
    load_dotenv()
    load_secrets_fron_env()
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
    main() #4200 to be used