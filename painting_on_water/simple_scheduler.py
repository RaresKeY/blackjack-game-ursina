from ursina import time

DEBUG = False

# TODO: FIX pop items immediately, take account of time separately

class SAction:
    def __init__(self, action, duration = 0.0, start_time = 0.0):
        self.start_time = start_time
        self.action = action
        self.duration = duration
        self.started = False
        self.endtime = 0

    def process_action(self, game_time):
        if not self.started:
            if DEBUG: print("started action")
            self.action()
            self.started = True
            self.endtime = game_time + self.duration

class ScheduleSeq:
    __slots__ = ("game_time", "sequence", "__dict__")
    def __init__(self):
        self.game_time = 0.0
        self.sequence = []
        self.test = 1

    def add_action(self, action, duration = 0.0):
        self.sequence.append(SAction(action, duration))

    def update(self):
        self.game_time += time.dt # type: ignore

        if not self.sequence:
            return

        # process action
        current_action = self.sequence[0]
        current_action.process_action(self.game_time)

        if self.game_time >= current_action.endtime:
            if DEBUG: print("action ended")
            self.sequence.pop(0)
            return
