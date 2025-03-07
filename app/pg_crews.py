import streamlit as st
from streamlit import session_state as ss
from app.my_crew import MyCrew
from app import db_utils

class PageCrews:
    def __init__(self):
        self.name = "Crews"

    def create_crew(self):
        crew = MyCrew()
        # if 'crews' not in ss:
        #     ss.crews = [MyCrew]
        # ss.crews.append(crew)
        crew.edit = True
        db_utils.save_crew(crew)  # Save crew to database
        return crew

