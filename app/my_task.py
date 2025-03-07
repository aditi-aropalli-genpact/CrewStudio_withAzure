from crewai import Task
import streamlit as st
from app.utils import generate_task_id, rnd_id, fix_columns_width
from streamlit import session_state as ss
from app.db_utils import save_task, delete_task
from datetime import datetime

class MyTask:
    def __init__(self, id=None, description=None, expected_output=None, agent=None, async_execution=None, created_at=None, context_from_async_tasks_ids=None, context_from_sync_tasks_ids=None,user_id=None, **kwargs):
        self.id = id or generate_task_id(user_id) 
        self.description = description or "Identify the next big trend in AI. Focus on identifying pros and cons and the overall narrative."
        self.expected_output = expected_output or "A comprehensive 3 paragraphs long report on the latest AI trends."
        self.agent = agent or ss.agents[0] if ss.agents else None
        self.async_execution = async_execution or False
        self.context_from_async_tasks_ids = context_from_async_tasks_ids or None
        self.context_from_sync_tasks_ids = context_from_sync_tasks_ids or None
        self.created_at = created_at or datetime.now().isoformat()
        self.edit_key = f'edit_{self.id}'
        # if self.edit_key not in ss:
        #     ss[self.edit_key] = False

    # @property
    # def edit(self):
    #     return ss[self.edit_key]

    # @edit.setter
    # def edit(self, value):
    #     ss[self.edit_key] = value

    def get_crewai_task(self, context_from_async_tasks=None, context_from_sync_tasks=None) -> Task:
        context = []
        if context_from_async_tasks:
            context.extend(context_from_async_tasks)
        if context_from_sync_tasks:
            context.extend(context_from_sync_tasks)
        
        if context:
            return Task(description=self.description, expected_output=self.expected_output, async_execution=self.async_execution, agent=self.agent.get_crewai_agent(), context=context)
        else:
            return Task(description=self.description, expected_output=self.expected_output, async_execution=self.async_execution, agent=self.agent.get_crewai_agent())

    def delete(self):
        # ss.tasks = [task for task in ss.tasks if task.id != self.id]
        delete_task(self.id)

    def is_valid(self, show_warning=False):
        if not self.agent:
            if show_warning:
                print(f"Task {self.description} has no agent")
            return False
        if not self.agent.is_valid(show_warning):
            return False
        return True

    # def draw(self, key=None):
    #     agent_options = [agent.role for agent in ss.agents]
    #     expander_title = f"({self.agent.role if self.agent else 'unassigned'}) - {self.description}" if self.is_valid() else f"❗ ({self.agent.role if self.agent else 'unassigned'}) - {self.description}"
    #     if self.edit:
    #         with st.expander(expander_title, expanded=True):
    #             with st.form(key=f'form_{self.id}' if key is None else key):
    #                 self.description = st.text_area("Description", value=self.description)
    #                 self.expected_output = st.text_area("Expected output", value=self.expected_output)
    #                 self.agent = st.selectbox("Agent", options=ss.agents, format_func=lambda x: x.role, index=0 if self.agent is None else agent_options.index(self.agent.role))
    #                 self.async_execution = st.checkbox("Async execution", value=self.async_execution)
    #                 self.context_from_async_tasks_ids = st.multiselect("Context from async tasks", options=[task.id for task in ss.tasks if task.async_execution], default=self.context_from_async_tasks_ids, format_func=lambda x: [task.description[:120] for task in ss.tasks if task.id == x][0])
    #                 self.context_from_sync_tasks_ids = st.multiselect("Context from sync tasks", options=[task.id for task in ss.tasks if not task.async_execution], default=self.context_from_sync_tasks_ids, format_func=lambda x: [task.description[:120] for task in ss.tasks if task.id == x][0])
    #                 submitted = st.form_submit_button("Save")
    #                 if submitted:
    #                     self.set_editable(False)
    #     else:
    #         fix_columns_width()
    #         with st.expander(expander_title):
    #             st.markdown(f"**Description:** {self.description}")
    #             st.markdown(f"**Expected output:** {self.expected_output}")
    #             st.markdown(f"**Agent:** {self.agent.role if self.agent else 'None'}")
    #             st.markdown(f"**Async execution:** {self.async_execution}")
    #             st.markdown(f"**Context from async tasks:** {', '.join([task.description[:120] for task in ss.tasks if task.id in self.context_from_async_tasks_ids]) if self.context_from_async_tasks_ids else 'None'}")
    #             st.markdown(f"**Context from sync tasks:** {', '.join([task.description[:120] for task in ss.tasks if task.id in self.context_from_sync_tasks_ids]) if self.context_from_sync_tasks_ids else 'None'}")
    #             col1, col2 = st.columns(2)
    #             with col1:
    #                 st.button("Edit", on_click=self.set_editable, args=(True,), key=rnd_id())
    #             with col2:
    #                 st.button("Delete", on_click=self.delete, key=rnd_id())
    #             self.is_valid(show_warning=True)

    # def set_editable(self, edit):
    #     self.edit = edit
    #     save_task(self)
    #     if not edit:
    #         st.rerun()

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from uuid import uuid4
from datetime import datetime
from app.db_utils import save_task, load_tasks, delete_task
# from app.auth import get_current_user
from app.my_task import MyTask

router = APIRouter()

class TaskCreate(BaseModel):
    description: str
    expected_output: str
    agent_id: Optional[str] = None
    async_execution: bool = False
    context_from_async_tasks_ids: List[str] = []
    context_from_sync_tasks_ids: List[str] = []

@router.post("/api/tasks/create")
async def create_task(task_data: TaskCreate):
    user_id = 'user'
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    task_id = "T_" + str(uuid4())[:8]
    created_at = datetime.now().isoformat()

    task = MyTask(
        id=task_id,
        description=task_data.description,
        expected_output=task_data.expected_output,
        agent_id=task_data.agent_id,
        async_execution=task_data.async_execution,
        context_from_async_tasks_ids=task_data.context_from_async_tasks_ids,
        context_from_sync_tasks_ids=task_data.context_from_sync_tasks_ids,
        created_at=created_at
    )

    save_task(task)
    return {"id": task.id}

@router.delete("/api/tasks/{task_id}/delete")
async def del_task(task_id: str):
    user_id = 'user'
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")
    delete_task(task_id)
    return {"detail": "Task deleted successfully"}

class TaskUpdate(BaseModel):
    description: Optional[str] = None
    expected_output: Optional[str] = None
    agent_id: Optional[str] = None
    async_execution: Optional[bool] = None
    context_from_async_tasks_ids: Optional[List[str]] = None
    context_from_sync_tasks_ids: Optional[List[str]] = None

@router.put("/api/tasks/{task_id}/edit")
async def edit_task(task_id: str, task_data: TaskUpdate):
    user_id = 'user'
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")

    tasks = load_tasks(user_id)
    task = next((t for t in tasks if t.id == task_id), None)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_fields = task_data.dict(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(task, field, value)

    save_task(task)
    return {"detail": "Task updated successfully"}

@router.get("/api/tasks/list")
async def get_tasks_list(user_id, view_mode):
    return load_tasks(user_id)
