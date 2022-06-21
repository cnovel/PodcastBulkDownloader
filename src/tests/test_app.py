from tkinter import *
from src import app


def test_app():
    root = Tk()
    a = app.PDBApp(root)
    for i in range(0, 3):
        a._cb_prefix.current(i)
        a.download()
        a.fetch()
        a.cancel()
