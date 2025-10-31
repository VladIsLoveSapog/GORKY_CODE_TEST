from aiogram.fsm.state import State, StatesGroup

class SurveyStates(StatesGroup):
    interests = State()    
    time = State()
    location = State()