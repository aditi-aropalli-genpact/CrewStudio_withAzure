from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app import db_utils
from app.pg_agents import PageAgents
from app.pg_tasks import PageTasks
from app.pg_crews import PageCrews
from app.pg_tools import PageTools
from app.pg_crew_run import PageCrewRun
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
  
# Create a router for agent-related endpoints  
agent_router = APIRouter()  

# Okta Authentication (if needed)
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

def get_okta_client():
    config = {
        'orgUrl': os.getenv("OKTA_ORG_URL"),
        'clientId': os.getenv("OKTA_CLIENT_ID"),
        'authorizationServerId': os.getenv("OKTA_AUTHORIZATION_SERVER_ID")
    }
    return OktaClient(config)

def pages():
    return {
        'crews': PageCrews(),
        'tools': PageTools(),
        'agents': PageAgents(),
        'tasks': PageTasks(),
        'kickoff': PageCrewRun(),
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

  

#API to create agents
class AgentCreate(BaseModel):  
    role: str  
    backstory: str  
    goal: str  
    temperature: float = 0.1  
    allow_delegation: bool = False  
    verbose: bool = True  
    cache: bool = True  
    llm_provider_model: str  
    max_iter: int = 25  
    tool_ids: List[str] = []  
  
@app.post('/api/agents')  
async def create_agent(  
    agent_data: AgentCreate,  
    token_payload: dict = Depends(verify_token)  
):  
    # Extract user_id from 'OHR' field in the token payload  
    user_id = token_payload.get('OHR')  
    if not user_id:  
        raise HTTPException(status_code=401, detail='User ID not found in token')  
  
    # Proceed to create the agent with this user_id  
    agent_id = 'A_' + str(uuid4())[:8]  
    created_at = datetime.now().isoformat()  
  
    # Load tools for the user  
    tools_list = load_tools(user_id)  
    tools_dict = {tool.tool_id: tool for tool in tools_list}  
  
    # Validate and collect selected tools  
    selected_tools = []  
    for tool_id in agent_data.tool_ids:  
        if tool_id in tools_dict:  
            selected_tools.append(tools_dict[tool_id])  
        else:  
            raise HTTPException(status_code=400, detail=f"Tool with ID '{tool_id}' not found")  
  
    # Create a new agent instance  
    agent = MyAgent(  
        id=agent_id,  
        role=agent_data.role,  
        backstory=agent_data.backstory,  
        goal=agent_data.goal,  
        temperature=agent_data.temperature,  
        allow_delegation=agent_data.allow_delegation,  
        verbose=agent_data.verbose,  
        cache=agent_data.cache,  
        llm_provider_model=agent_data.llm_provider_model,  
        max_iter=agent_data.max_iter,  
        tools=selected_tools,  
        created_at=created_at  
    )  
    agent.creator_id = user_id  # Set the creator_id to the user ID from the token  
  
    # Save the agent to the database  
    save_agent(agent)  
  
    # Return the created agent's ID  
    return {'id': agent.id}  

  
# Endpoint to delete an agent  
@app.delete('/api/agents/{agent_id}')  
async def delete_agent(  
    agent_id: str,  
    token_payload: dict = Depends(verify_token)  
):  
    # Extract user_id from 'OHR' field in the token payload  
    user_id = token_payload.get('OHR')  
    if not user_id:  
        raise HTTPException(status_code=401, detail='User ID not found in token')  
  
    # Load agent to ensure it exists and belongs to the user  
    agents = db_utils.load_agents(user_id)  
    agent = next((a for a in agents if a.id == agent_id), None)  
    if not agent:  
        raise HTTPException(status_code=404, detail='Agent not found')  
  
    # Delete the agent  
    db_utils.delete_agent(agent_id)  
    return {'detail': 'Agent deleted successfully'}  



  
# Define Pydantic model for agent update  
class AgentUpdate(BaseModel):  
    role: Optional[str] = None  
    backstory: Optional[str] = None  
    goal: Optional[str] = None  
    temperature: Optional[float] = None  
    allow_delegation: Optional[bool] = None  
    verbose: Optional[bool] = None  
    cache: Optional[bool] = None  
    llm_provider_model: Optional[str] = None  
    max_iter: Optional[int] = None  
    tool_ids: Optional[List[str]] = None  
  
# Endpoint to edit an agent  
@app.put('/api/agents/{agent_id}')  
async def edit_agent(  
    agent_id: str,  
    agent_data: AgentUpdate,  
    token_payload: dict = Depends(verify_token)  
):  
    # Extract user_id from 'OHR' field in the token payload  
    user_id = token_payload.get('OHR')  
    if not user_id:  
        raise HTTPException(status_code=401, detail='User ID not found in token')  
  
    # Load agents and find the one to edit  
    agents = db_utils.load_agents(user_id)  
    agent = next((a for a in agents if a.id == agent_id), None)  
  
    if not agent:  
        raise HTTPException(status_code=404, detail='Agent not found')  
  
    # Update agent fields if provided  
    update_fields = agent_data.dict(exclude_unset=True)  
  
    # If tools are being updated, load and validate them  
    if 'tool_ids' in update_fields:  
        tools_list = db_utils.load_tools(user_id)  
        tools_dict = {tool.tool_id: tool for tool in tools_list}  
        selected_tools = []  
        for tool_id in update_fields['tool_ids']:  
            if tool_id in tools_dict:  
                selected_tools.append(tools_dict[tool_id])  
            else:  
                raise HTTPException(status_code=400, detail=f"Tool with ID '{tool_id}' not found")  
        agent.tools = selected_tools  
        del update_fields['tool_ids']  
  
    # Update other fields  
    for field, value in update_fields.items():  
        setattr(agent, field, value)  
  
    # Save the updated agent  
    db_utils.save_agent(agent)  
    return {'detail': 'Agent updated successfully'}  


# Endpoint to publish an agent  
@app.patch('/api/agents/{agent_id}/publish')  
async def publish_agent(  
    agent_id: str,  
    token_payload: dict = Depends(verify_token)  
):  
    # Extract user_id from 'OHR' field in the token payload  
    user_id = token_payload.get('OHR')  
    if not user_id:  
        raise HTTPException(status_code=401, detail='User ID not found in token')  
  
    # Load agents and find the one to publish  
    agents = db_utils.load_agents(user_id)  
    agent = next((a for a in agents if a.id == agent_id), None)  
  
    if not agent:  
        raise HTTPException(status_code=404, detail='Agent not found')  
  
    # Publish the agent  
    db_utils.publish_agent(agent_id, user_id)  
    return {'detail': 'Agent published successfully'}  