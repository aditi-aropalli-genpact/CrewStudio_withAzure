from crewai import Crew, Process
from datetime import datetime
from app.utils import rnd_id
from app.llms import llm_providers_and_models, create_llm
from app import db_utils

class MyCrew:
    def __init__(self, id=None, name=None, agents=None, tasks=None, process=None, cache=None, max_rpm=None, verbose=None, manager_llm=None, manager_agent=None, created_at=None, memory=None, planning=None):
        self.id = id or "C_" + rnd_id()
        self.name = name or "Crew 1"
        self.agents = agents or []
        self.tasks = tasks or []
        self.process = process or Process.sequential
        self.verbose = bool(verbose) if verbose is not None else True
        self.manager_llm = manager_llm
        self.manager_agent = manager_agent
        self.memory = memory if memory is not None else False
        self.cache = cache if cache is not None else True
        self.max_rpm = max_rpm or 1000
        self.planning = planning if planning is not None else False
        self.created_at = created_at or datetime.now().isoformat()
        self.edit = False  # Replaces session state `edit_key`

    def get_crewai_crew(self) -> Crew:
        """Creates and returns a CrewAI Crew object with correct dependencies."""
        crewai_agents = [agent.get_crewai_agent() for agent in self.agents]
        task_objects = {}

        def create_task(task):
            if task.id in task_objects:
                return task_objects[task.id]

            context_tasks = []
            for context_task_id in (task.context_from_async_tasks_ids or []) + (task.context_from_sync_tasks_ids or []):
                context_task = next((t for t in self.tasks if t.id == context_task_id), None)
                if context_task:
                    context_tasks.append(create_task(context_task))

            crewai_task = task.get_crewai_task(context_from_async_tasks=context_tasks) if task.async_execution or context_tasks else task.get_crewai_task()
            task_objects[task.id] = crewai_task
            return crewai_task

        crewai_tasks = [create_task(task) for task in self.tasks]

        return Crew(
            agents=crewai_agents,
            tasks=crewai_tasks,
            cache=self.cache,
            process=self.process,
            max_rpm=self.max_rpm,
            verbose=self.verbose,
            manager_llm=create_llm(self.manager_llm) if self.manager_llm else None,
            manager_agent=self.manager_agent.get_crewai_agent() if self.manager_agent else None,
            memory=self.memory,
            planning=self.planning
        )

    def delete(self):
        """Deletes crew from the database."""
        db_utils.delete_crew(self.id)

    def publish(self):
        """Publishes crew configuration."""
        db_utils.publish_crew(self.id)

    def update(self, name=None, process=None, agents=None, tasks=None, verbose=None, manager_llm=None, manager_agent=None, memory=None, cache=None, max_rpm=None, planning=None):
        """Updates crew properties dynamically."""
        if name is not None:
            self.name = name
        if process is not None:
            self.process = process
        if agents is not None:
            self.agents = agents
        if tasks is not None:
            self.tasks = tasks
        if verbose is not None:
            self.verbose = verbose
        if manager_llm is not None:
            self.manager_llm = manager_llm
        if manager_agent is not None:
            self.manager_agent = manager_agent
        if memory is not None:
            self.memory = memory
        if cache is not None:
            self.cache = cache
        if max_rpm is not None:
            self.max_rpm = max_rpm
        if planning is not None:
            self.planning = planning
        db_utils.save_crew(self)

    def is_valid(self):
        """Validates the crew setup."""
        if not self.agents:
            return False, "Crew has no agents"
        if not self.tasks:
            return False, "Crew has no tasks"
        if any(not agent.is_valid() for agent in self.agents):
            return False, "One or more agents are invalid"
        if any(not task.is_valid() for task in self.tasks):
            return False, "One or more tasks are invalid"
        if self.process == Process.hierarchical and not (self.manager_llm or self.manager_agent):
            return False, "Hierarchical process requires a manager LLM or manager agent"
        return True, "Crew is valid"

    def validate_manager_llm(self):
        """Ensures the manager LLM exists in available models."""
        available_models = llm_providers_and_models()
        if self.manager_llm and self.manager_llm not in available_models:
            self.manager_llm = None
