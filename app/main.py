from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app import db_utils
from app.pg_agents import PageAgents
from app.pg_tasks import PageTasks
from app.pg_crews import PageCrews
from app.pg_tools import PageTools
from app import pg_crew_run 
from app.pg_export_crew import PageExportCrew
from app.pg_results import PageResults
from dotenv import load_dotenv
from app.llms import load_secrets_fron_env
import os
from typing import AsyncGenerator,List,Optional
from app.okta_auth import verify_token, get_current_user
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from pydantic import BaseModel  
from uuid import uuid4  
from datetime import datetime  
from typing import List  
from app.okta_auth import verify_token  
from app.my_agent import MyAgent  
from app.db_utils import save_agent, load_tools 
from typing import Optional   
from app import my_agent, my_task, my_tools, my_crew

import streamlit as st
if 'agents' not in st.session_state:
    st.session_state.agents = []

# Define lifespan as an async generator
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    db_utils.initialize_db()
    if str(os.getenv('AGENTOPS_ENABLED')).lower() in ['true', '1']:
        try:
            import agentops
            agentops.init(api_key=os.getenv('AGENTOPS_API_KEY'), auto_start_session=False)
        except ModuleNotFoundError as e:
            print(f"Error initializing AgentOps: {str(e)}")
    yield  # Let FastAPI run the app

app = FastAPI(lifespan=lifespan)

app.include_router(my_agent.router, #
                #    dependencies=[Depends(verify_token)]
                )
app.include_router(pg_crew_run.router, 
                #    dependencies = [Depends(verify_token)]
                   )
app.include_router(my_crew.router)
app.include_router(my_task.router)



# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load environment variables
load_dotenv()
load_secrets_fron_env()

def pages():
    return {
        'crews': PageCrews(),
        'tools': PageTools(),
        'agents': PageAgents(),
        'tasks': PageTasks(),
        # 'kickoff': PageCrewRun(),
        'results': PageResults(),
        'import_export': PageExportCrew()
    }

def load_data(user_id, view_mode='published'): #mine 
    return {
        "agents": db_utils.load_agents(user_id, view_mode),
        "tasks": db_utils.load_tasks(user_id),
        "crews": db_utils.load_crews(user_id),
        "tools": db_utils.load_tools(user_id),
        "enabled_tools": db_utils.load_tools_state()
    }

@app.get("/api/data")
async def get_data(user_id):
    return load_data(user_id)

@app.get("/api/{page}")
async def get_page_data(page: str, user_id, view_mode,
                        # token_payload: dict = Depends(verify_token)
                        ):
    if page not in pages():
        return {"error": "Page not found"}
    return {"page": page, "data": load_data(user_id, view_mode)}