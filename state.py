from aiogram.fsm.state import State, StatesGroup

class UserState(StatesGroup):
    waiting_for_interests = State()
    waiting_for_time = State()
    waiting_for_location = State()
