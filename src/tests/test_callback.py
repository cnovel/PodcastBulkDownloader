from tkinter.ttk import Progressbar
from src import callback


def test_callback_pb():
    pb = Progressbar()
    cb = callback.Callback(pb)
    cb.progress(1)
    assert cb._progress == 1
    if cb._pb:
        assert cb._pb['value'] == 1


def test_callback_function():
    cb = callback.Callback()
    cb.set_function(lambda x: 2*x)
    cb.progress(1)
    assert cb._progress == 2


def test_callback_cancel():
    cb = callback.Callback()
    assert not cb.is_cancelled()
    cb.cancel()
    assert cb.is_cancelled()
    cb.reset()
    assert not cb.is_cancelled()


def test_reset_progress():
    cb = callback.Callback()
    cb.progress(1)
    assert cb._progress != 0
    cb.reset()
    assert cb._progress == 0
