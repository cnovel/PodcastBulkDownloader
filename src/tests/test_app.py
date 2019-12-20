from os import environ
from tkinter import *
from src import app


def test_app():
    # Can't test if no display
    if environ.get('DISPLAY', '') != '':
        root = Tk()
        a = app.PDBApp(root)
        a.download()
        a.fetch()
        a.cancel()
