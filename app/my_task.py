from crewai import Task
from datetime import datetime
from app.utils import rnd_id
from app.db_utils import save_task, delete_task, publish_task

class MyTask:
    def __init__(self, id=None, description=None, expected_output=None, agent=None, async_execution=None, created_at=None, context_from_async_tasks_ids=None, context_from_sync_tasks_ids=None, **kwargs):
        self.id = id or "T_" + rnd_id()
        self.description = description or "Identify the next big trend in AI. Focus on identifying pros and cons and the overall narrative."
        self.expected_output = expected_output or "A comprehensive 3 paragraphs long report on the latest AI trends."
        self.agent = agent  # Expecting agent to be passed explicitly from frontend
        self.async_execution = async_execution if async_execution is not None else False
        self.context_from_async_tasks_ids = context_from_async_tasks_ids or []
        self.context_from_sync_tasks_ids = context_from_sync_tasks_ids or []
        self.created_at = created_at or datetime.now().isoformat()

    def get_crewai_task(self, context_from_async_tasks=None, context_from_sync_tasks=None) -> Task:
        context = []
        if context_from_async_tasks:
            context.extend(context_from_async_tasks)
        if context_from_sync_tasks:
            context.extend(context_from_sync_tasks)

        return Task(
            description=self.description,
            expected_output=self.expected_output,
            async_execution=self.async_execution,
            agent=self.agent.get_crewai_agent() if self.agent else None,
            context=context if context else None
        )

    def delete(self):
        delete_task(self.id)

    def publish(self):
        publish_task(self.id)

    def is_valid(self):
        return bool(self.agent and self.agent.is_valid())

    def to_dict(self):
        return {
            "id": self.id,
            "description": self.description,
            "expected_output": self.expected_output,
            "agent_id": self.agent.id if self.agent else None,
            "async_execution": self.async_execution,
            "context_from_async_tasks_ids": self.context_from_async_tasks_ids,
            "context_from_sync_tasks_ids": self.context_from_sync_tasks_ids,
            "created_at": self.created_at,
            "is_valid": self.is_valid()
        }

    @classmethod
    def from_dict(cls, data, agents):
        agent = next((agent for agent in agents if agent.id == data.get("agent_id")), None)
        return cls(
            id=data.get("id"),
            description=data.get("description"),
            expected_output=data.get("expected_output"),
            agent=agent,
            async_execution=data.get("async_execution"),
            context_from_async_tasks_ids=data.get("context_from_async_tasks_ids"),
            context_from_sync_tasks_ids=data.get("context_from_sync_tasks_ids"),
            created_at=data.get("created_at")
        )