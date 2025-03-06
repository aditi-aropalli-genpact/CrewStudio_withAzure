from fastapi import APIRouter, BackgroundTasks, HTTPException
import re
import queue
import time
import traceback
import os
import threading
import ctypes
from  app.console_capture import ConsoleCapture
from app.db_utils import load_results, save_result, load_crew_by_name
from app.utils import format_result, generate_printable_view, rnd_id

router = APIRouter()

class PageCrewRun:
    def __init__(self):
        self.name = "Kickoff!"
        self.maintain_session_state()
        if 'results' not in self.session_state:
            self.session_state['results'] = load_results()
    
    @property
    def session_state(self):
        if not hasattr(self, '_session_state'):
            self._session_state = {}
        return self._session_state
    
    # @staticmethod
    def maintain_session_state(self):
        defaults = {
            'crew_thread': None,
            'result': None,
            'running': False,
            'message_queue': queue.Queue(),
            'selected_crew_name': None,
            'placeholders': {},
            'console_output': [],
            'last_update': time.time(),
            'console_expanded': True,
        }
        for key, value in defaults.items():
            if key not in self.session_state:
                self.session_state[key] = value


    @staticmethod
    def extract_placeholders(text):
        return re.findall(r'\{(.*?)\}', text)

    def get_placeholders_from_crew(self, crew):
        placeholders = set()
        attributes = ['description', 'expected_output', 'role', 'backstory', 'goal']
        
        for task in crew.tasks:
            placeholders.update(self.extract_placeholders(task.description))
            placeholders.update(self.extract_placeholders(task.expected_output))
        
        for agent in crew.agents:
            for attr in attributes[2:]:
                placeholders.update(self.extract_placeholders(getattr(agent, attr)))
        
        return placeholders

    def run_crew(self, crewai_crew, inputs, message_queue):
        if (str(os.getenv('AGENTOPS_ENABLED')).lower() in ['true', '1']) and not self.session_state.get('agentops_failed', False):
            import agentops
            agentops.start_session()
        try:
            result = crewai_crew.kickoff(inputs=inputs)
            message_queue.put({"result": result})
        except Exception as e:
            if (str(os.getenv('AGENTOPS_ENABLED')).lower() in ['true', '1']) and not self.session_state.get('agentops_failed', False):
                agentops.end_session()
            stack_trace = traceback.format_exc()
            print(f"Error running crew: {str(e)}\n{stack_trace}")
            message_queue.put({"result": f"Error running crew: {str(e)}", "stack_trace": stack_trace})
        finally:
            if hasattr(self.session_state, 'console_capture'):
                self.session_state['console_capture'].stop()

    def get_mycrew_by_name(self, crewname):
        return next((crew for crew in self.session_state.get('crews', []) if crew.name == crewname), None)
    
    def control_buttons(self, selected_crew):
        if not selected_crew.is_valid() or self.session_state['running']:
            return
        
        inputs = {key.split('_')[1]: value for key, value in self.session_state['placeholders'].items()}
        self.session_state['result'] = None
        
        try:
            crew = selected_crew.get_crewai_crew(full_output=True)
        except Exception as e:
            print(traceback.format_exc())
            return
        
        self.session_state['console_capture'] = ConsoleCapture()
        self.session_state['console_capture'].start()
        self.session_state['console_output'] = []
        self.session_state['running'] = True
        
        self.session_state['crew_thread'] = threading.Thread(
            target=self.run_crew,
            kwargs={
                "crewai_crew": crew,
                "inputs": inputs,
                "message_queue": self.session_state['message_queue']
            }
        )
        self.session_state['crew_thread'].start()
    
    @staticmethod
    def force_stop_thread(thread):
        if thread:
            tid = ctypes.c_long(thread.ident)
            if tid:
                res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(SystemExit))
                if res == 0:
                    print("Nonexistent thread id")
                else:
                    print("Thread stopped successfully.")

    def get_result(self):
        try:
            message = self.session_state['message_queue'].get_nowait()
            self.session_state['result'] = message
            self.session_state['running'] = False
            if hasattr(self.session_state, 'console_capture'):
                self.session_state['console_capture'].stop()
        except queue.Empty:
            return None
        return self.serialize_result(self.session_state['result'])
    
    def serialize_result(self, result):
        if isinstance(result, dict):
            serialized = {}
            for key, value in result.items():
                if hasattr(value, 'raw'):
                    serialized[key] = {'raw': value.raw, 'type': 'CrewOutput'}
                elif hasattr(value, '__dict__'):
                    serialized[key] = {'data': value.__dict__, 'type': value.__class__.__name__}
                else:
                    serialized[key] = value
            return serialized
        return str(result)

    def clear_console(self):
        self.session_state['console_output'] = []

    def list_available_crews(self):
        return [crew.name for crew in self.session_state.get('crews', [])]

crew_run = PageCrewRun()

from pydantic import BaseModel

class RunCrewRequest(BaseModel):
    crew_name: str


@router.post("/run_crew")
def api_run_crew(request: RunCrewRequest):
    selected_crew = request.crew_name

    # Fetch MyCrew instance from DB
    crew_instance = load_crew_by_name(selected_crew)

    if not crew_instance:
        raise HTTPException(status_code=404, detail=f"Crew '{selected_crew}' not found")

    try:
        # Convert MyCrew to Crew and run it
        crew_ai_instance = crew_instance.get_crewai_crew()  
        result = crew_ai_instance.kickoff()
        print(f"Execution result: {result}")
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error running crew: {error_details}")
        raise HTTPException(
            status_code=500,
            detail=f"Error running Crew: {str(e)}"
        )

    return {
        "message": f"Crew '{selected_crew}' executed successfully.",
        "execution_result": result
    }


@router.post("/stop_crew")
def api_stop_crew():
    if not crew_run.session_state['running']:
        raise HTTPException(status_code=400, detail="No crew is currently running.")
    crew_run.force_stop_thread(crew_run.session_state['crew_thread'])
    crew_run.session_state['running'] = False
    crew_run.session_state['crew_thread'] = None
    return {"message": "Crew execution stopped."}

@router.get("/get_result")
def api_get_result():
    result = crew_run.get_result()
    if result is None:
        raise HTTPException(status_code=404, detail="No result available yet.")
    return {"result": result}

@router.post("/clear_console")
def api_clear_console():
    crew_run.clear_console()
    return {"message": "Console cleared."}

@router.get("/list_crews")
def api_list_crews():
    return {"crews": crew_run.list_available_crews()}
