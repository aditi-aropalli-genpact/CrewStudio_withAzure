from crewai import Agent
import streamlit as st
from app.utils import rnd_id, fix_columns_width
from streamlit import session_state as ss
from app.db_utils import save_agent, delete_agent
from app.llms import llm_providers_and_models, create_llm
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from app import db_utils
from app.okta_auth import verify_token, get_current_user
from uuid import uuid4  
class MyAgent:
    def __init__(self, id=None, role=None, backstory=None, goal=None, temperature=None, allow_delegation=False, verbose=False, cache= None, llm_provider_model=None, max_iter=None, created_at=None, tools=None):
        self.id = id or "A_" + rnd_id()
        self.role = role or "Senior Researcher"
        self.backstory = backstory or "Driven by curiosity, you're at the forefront of innovation, eager to explore and share knowledge that could change the world."
        self.goal = goal or "Uncover groundbreaking technologies in AI"
        self.temperature = temperature or 0.1
        self.allow_delegation = allow_delegation if allow_delegation is not None else False
        self.verbose = verbose if verbose is not None else True
        self.llm_provider_model = llm_providers_and_models()[0] if llm_provider_model is None else llm_provider_model
        self.created_at = created_at or datetime.now().isoformat()
        self.tools = tools or []
        self.max_iter = max_iter or 25
        self.cache = cache if cache is not None else True
        self.edit_key = f'edit_{self.id}'
        # if self.edit_key not in ss:
        #     ss[self.edit_key] = False

    # @property
    # def edit(self):
    #     return ss[self.edit_key]

    # @edit.setter
    # def edit(self, value):
    #     ss[self.edit_key] = value

    def get_crewai_agent(self) -> Agent:
            llm = create_llm(self.llm_provider_model, temperature=self.temperature)
            tools = [tool.create_tool() for tool in self.tools]
            return Agent(
                role=self.role,
                backstory=self.backstory,
                goal=self.goal,
                allow_delegation=self.allow_delegation,
                verbose=self.verbose,
                max_iter=self.max_iter,
                cache=self.cache,
                tools=tools,
                llm=llm
            )

    def delete(self):
        # ss.agents = [agent for agent in ss.agents if agent.id != self.id]
        delete_agent(self.id)

    def get_tool_display_name(self, tool):
        first_param_name = tool.get_parameter_names()[0] if tool.get_parameter_names() else None
        first_param_value = tool.parameters.get(first_param_name, '') if first_param_name else ''
        return f"{tool.name} ({first_param_value if first_param_value else tool.tool_id})"

    def is_valid(self, show_warning=False):
        for tool in self.tools:
            if not tool.is_valid(show_warning=show_warning):
                if show_warning:
                    print(f"Tool {tool.name} is not valid")
                return False
        return True

    def validate_llm_provider_model(self):
        available_models = llm_providers_and_models()
        if self.llm_provider_model not in available_models:
            self.llm_provider_model = available_models[0]

    # def draw(self, key=None):
    #     self.validate_llm_provider_model()
    #     expander_title = f"{self.role[:60]} -{self.llm_provider_model.split(':')[1]}" if self.is_valid() else f"❗ {self.role[:20]} -{self.llm_provider_model.split(':')[1]}"
    #     if self.edit:
    #         with st.expander(f"Agent: {self.role}", expanded=True):
    #             with st.form(key=f'form_{self.id}' if key is None else key):
    #                 self.role = st.text_input("Role", value=self.role)
    #                 self.backstory = st.text_area("Backstory", value=self.backstory)
    #                 self.goal = st.text_area("Goal", value=self.goal)
    #                 self.allow_delegation = st.checkbox("Allow delegation", value=self.allow_delegation)
    #                 self.verbose = st.checkbox("Verbose", value=self.verbose)
    #                 self.cache = st.checkbox("Cache", value=self.cache)
    #                 self.llm_provider_model = st.selectbox("LLM Provider and Model", options=llm_providers_and_models(), index=llm_providers_and_models().index(self.llm_provider_model))
    #                 self.temperature = st.slider("Temperature", value=self.temperature, min_value=0.0, max_value=1.0)
    #                 self.max_iter = st.number_input("Max Iterations", value=self.max_iter, min_value=1, max_value=100)
    #                 enabled_tools = [tool for tool in ss.tools]
    #                 selected_tools = st.multiselect(
    #                     "Select Tools",
    #                     [self.get_tool_display_name(tool) for tool in enabled_tools],
    #                     default=[self.get_tool_display_name(tool) for tool in self.tools],
    #                     key=f"{self.id}_tools{key}"
    #                 )

    #         st.rerun()                    submitted = st.form_submit_button("Save")
    #                 if submitted:
    #                     self.tools = [tool for tool in enabled_tools if self.get_tool_display_name(tool) in selected_tools]
    #                     self.set_editable(False)
    #     else:
    #         fix_columns_width()
    #         with st.expander(expander_title, expanded=False):
    #             st.markdown(f"**Role:** {self.role}")
    #             st.markdown(f"**Backstory:** {self.backstory}")
    #             st.markdown(f"**Goal:** {self.goal}")
    #             st.markdown(f"**Allow delegation:** {self.allow_delegation}")
    #             st.markdown(f"**Verbose:** {self.verbose}")
    #             st.markdown(f"**Cache:** {self.cache}")
    #             st.markdown(f"**LLM Provider and Model:** {self.llm_provider_model}")
    #             st.markdown(f"**Temperature:** {self.temperature}")
    #             st.markdown(f"**Max Iterations:** {self.max_iter}")
    #             st.markdown(f"**Tools:** {[self.get_tool_display_name(tool) for tool in self.tools]}")

    #             self.is_valid(show_warning=True)

    #             col1, col2 = st.columns(2)
    #             with col1:
    #                 st.button("Edit", on_click=self.set_editable, args=(True,), key=rnd_id())
    #             with col2:
    #                 st.button("Delete", on_click=self.delete, key=rnd_id())

    # def set_editable(self, edit):
    #     self.edit = edit
    #     save_agent(self)
    #     if not edit:

    #API to create agents
router = APIRouter()

from pydantic import BaseModel
from typing import List
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
  
@router.post('/api/agents/create')  
async def create_agent(  
    agent_data: AgentCreate,  
    # token_payload: dict = Depends(verify_token)  
):  
    # Extract user_id from 'OHR' field in the token payload  
    # user_id = token_payload.get('OHR')  
    user_id = 'user'
    if not user_id:  
        raise HTTPException(status_code=401, detail='User ID not found in token')  
  
    # Proceed to create the agent with this user_id  
    agent_id = 'A_' + str(uuid4())[:8]  
    created_at = datetime.now().isoformat()  
  
    # Load tools for the user  
    tools_list = db_utils.load_tools(user_id)  
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
@router.delete('/api/agents/{agent_id}/delete')  
async def delete_agent(  
    agent_id: str,  
    # token_payload: dict = Depends(verify_token)  
):  
    # Extract user_id from 'OHR' field in the token payload  
    # user_id = token_payload.get('OHR')  
    user_id = 'user'
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
@router.put('/api/agents/{agent_id}/edit')  
async def edit_agent(  
    agent_id: str,  
    agent_data: AgentUpdate,  
    # token_payload: dict = Depends(verify_token)  
):  
    # Extract user_id from 'OHR' field in the token payload  
    # user_id = token_payload.get('OHR') 
    user_id = 'user' 
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
@router.patch('/api/agents/{agent_id}/publish')  
async def publish_agent(  
    agent_id: str,  
    # token_payload: dict = Depends(verify_token)  
):  
    # Extract user_id from 'OHR' field in the token payload  
    # user_id = token_payload.get('OHR')  
    user_id = 'user'
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

@router.get('api/agents/list')
async def get_agents_list(user_id, view_mode):
    return db_utils.load_agents(user_id, view_mode)