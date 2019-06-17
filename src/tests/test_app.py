from tkinter import *
from .. import app


def test_app():
    root = Tk()
    a = app.PDBApp(root)
    a.download()
    a.fetch()
    a.cancel()
