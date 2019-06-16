from tkinter.ttk import Progressbar


class Callback:
    def __init__(self, pb: Progressbar = None):
        self._continue = True
        self._progress = 0
        self._pb = pb
        self._f = lambda x: x

    def cancel(self):
        self._continue = False

    def is_cancelled(self):
        return not self._continue

    def reset(self):
        self._continue = True
        self._progress = 0
        if self._pb:
            self._pb['value'] = 0

    def set_function(self, f):
        self._f = f

    def progress(self, p: float):
        if p is not None:
            self._progress = self._f(p)
            if self._pb:
                self._pb['value'] = self._progress
        return self._progress
