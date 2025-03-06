from crewai import Agent
from datetime import datetime
from app.utils import rnd_id
from app.db_utils import save_agent, delete_agent, publish_agent
from app.llms import llm_providers_and_models, create_llm

class MyAgent:
    def __init__(self, id=None, role=None, backstory=None, goal=None, temperature=None, allow_delegation=False, verbose=False, cache=None, llm_provider_model=None, max_iter=None, created_at=None, tools=None):
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
        self.edit = False  # Replaces Streamlit session state

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
        delete_agent(self.id)

    def publish(self):
        publish_agent(self.id)

    def update(self, role=None, backstory=None, goal=None, temperature=None, allow_delegation=None, verbose=None, cache=None, llm_provider_model=None, max_iter=None, tools=None):
        if role is not None:
            self.role = role
        if backstory is not None:
            self.backstory = backstory
        if goal is not None:
            self.goal = goal
        if temperature is not None:
            self.temperature = temperature
        if allow_delegation is not None:
            self.allow_delegation = allow_delegation
        if verbose is not None:
            self.verbose = verbose
        if cache is not None:
            self.cache = cache
        if llm_provider_model is not None:
            self.llm_provider_model = llm_provider_model
        if max_iter is not None:
            self.max_iter = max_iter
        if tools is not None:
            self.tools = tools
        save_agent(self)

    def is_valid(self):
        for tool in self.tools:
            if not tool.is_valid():
                return False, f"Tool {tool.name} is not valid"
        return True, "Agent is valid"

    def validate_llm_provider_model(self):
        available_models = llm_providers_and_models()
        if self.llm_provider_model not in available_models:
            self.llm_provider_model = available_models[0]
