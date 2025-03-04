from fastapi import FastAPI, BackgroundTasks, HTTPException, APIRouter
from pydantic import BaseModel
import threading
import queue
import time
import os
import traceback
from app.console_capture import ConsoleCapture
from app.db_utils import load_results, save_result
from app.utils import format_result, generate_printable_view, rnd_id

router = APIRouter()

class CrewRunState:
    def __init__(self):
        self.crew_thread = None
        self.result = None
        self.running = False
        self.message_queue = queue.Queue()
        self.selected_crew_name = None
        self.placeholders = {}
        self.console_output = []
        self.last_update = time.time()
        self.console_expanded = True

state = CrewRunState()

class CrewRunRequest(BaseModel):
    crew_name: str
    inputs: dict

def get_mycrew_by_name(crew_name):
    for crew in load_results():  # Assuming crews are loaded here
        if crew.name == crew_name:
            return crew
    return None

def run_crew(crewai_crew, inputs, message_queue):
    try:
        result = crewai_crew.kickoff(inputs=inputs)
        message_queue.put({"result": result})
    except Exception as e:
        stack_trace = traceback.format_exc()
        print(f"Error running crew: {str(e)}\n{stack_trace}")
        message_queue.put({"result": f"Error running crew: {str(e)}", "stack_trace": stack_trace})
    finally:
        state.running = False

@router.post("/run_crew/")
def run_crew_api(request: CrewRunRequest, background_tasks: BackgroundTasks):
    if state.running:
        raise HTTPException(status_code=400, detail="A crew is already running.")
    
    crew = get_mycrew_by_name(request.crew_name)
    if not crew:
        raise HTTPException(status_code=404, detail="Crew not found.")
    
    state.running = True
    state.selected_crew_name = request.crew_name
    state.result = None
    state.message_queue.queue.clear()
    
    background_tasks.add_task(run_crew, crew.get_crewai_crew(full_output=True), request.inputs, state.message_queue)
    return {"message": "Crew execution started."}

@router.get("/get_result/")
def get_result():
    if not state.running and state.result is None:
        raise HTTPException(status_code=400, detail="No crew is running or result available.")
    
    try:
        message = state.message_queue.get_nowait()
        state.result = message
    except queue.Empty:
        pass
    
    return {"running": state.running, "result": state.result}
