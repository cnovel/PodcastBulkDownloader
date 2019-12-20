import os
import logging
from tkinter import *
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog
from threading import Thread
from src.bulk_downloader import BulkDownloader
from src.callback import Callback
from src import pbd_version


def show_message_box_on_exception(exc: Exception):
    messagebox.showerror(title='An exception occurred',
                         message='An exception occurred:\n{}'
                                 '\n\nDetails:\n{}'
                                 '\n\nPlease report the issue on GitHub'.format(exc, exc.args))

    exit(1)


class PDBApp(Frame):
    def __init__(self, master):
        Frame.__init__(self, master)
        master.title('Podcast Bulk Downloader v{}'.format(pbd_version))
        # master.geometry('500x800')
        style = ttk.Style()
        self._style = StringVar()
        if 'vista' in style.theme_names():
            self._style.set('vista')
        else:
            self._style.set('default')
        style.theme_use(self._style.get())

        # Layout configuration
        columns = 0
        while columns < 10:
            master.columnconfigure(columns, weight=1)
            columns += 1
        rows = 0
        while rows < 5:
            w = 1 if rows != 3 else 5
            master.rowconfigure(rows, weight=w)
            rows += 1

        # First line
        self._label_rss = ttk.Label(master, text='Feed')
        self._label_rss.grid(row=0, column=0, padx=2, pady=2, sticky=W+E)
        self._entry_rss = ttk.Entry(master)
        self._entry_rss.grid(row=0, column=1, padx=2, pady=2, columnspan=9, sticky=W+E)

        # Second line
        self._label_folder = ttk.Label(master, text='Folder')
        self._label_folder.grid(row=1, column=0, padx=2, sticky=W+E)
        self._entry_folder = ttk.Entry(master)
        self._entry_folder.grid(row=1, column=1, padx=2, columnspan=8, sticky=W+E)
        self._btn_nav = ttk.Button(master, text='...', command=self.browse_directory)
        self._btn_nav.grid(row=1, column=9, padx=2, pady=2, sticky=W+E)

        # Third line
        self._overwrite = IntVar()
        self._cb_overwrite = ttk.Checkbutton(master, text='Overwrite existing files',
                                             variable=self._overwrite, onvalue=1, offvalue=0)
        self._cb_overwrite.grid(row=2, column=0, columnspan=2, sticky=W+E, padx=2, pady=2)
        self._btn_fetch = ttk.Button(master, text='Fetch', command=self.fetch)
        self._btn_fetch.grid(row=2, column=7, columnspan=1, sticky=W+E, padx=2, pady=2)
        self._btn_download = ttk.Button(master, text='Download', command=self.download)
        self._btn_download.grid(row=2, column=8, columnspan=1, sticky=W+E, padx=2, pady=2)
        self._btn_cancel = ttk.Button(master, text='Cancel', command=self.cancel)
        self._btn_cancel.grid(row=2, column=9, columnspan=1, sticky=W+E, padx=2, pady=2)

        # Fourth line
        self._progress_bar = ttk.Progressbar(master, orient='horizontal', mode='determinate')
        self._progress_bar.grid(row=3, column=0, columnspan=10, sticky=W+E+N+S, padx=2, pady=2)
        self._progress_bar["maximum"] = 100

        # Fifth line
        self._text = Text(master)
        self._text.grid(row=4, column=0, columnspan=10, sticky=W+E+N+S, padx=2, pady=2)
        self._text.configure(state=DISABLED)

        self._logger = Log2Text(self._text)
        logging.getLogger().setLevel(logging.INFO)
        logging.getLogger().addHandler(self._logger)

        # Utilities
        self._dl = BulkDownloader(self._entry_rss.get(), self._entry_folder.get())
        self._dl_thread = Thread(target=None)
        self._fetch_thread = Thread(target=None)
        self._callback = Callback(self._progress_bar)

        # Launch background task
        self.reset_buttons()

    def reset_buttons(self):
        if not self._fetch_thread.is_alive() and not self._dl_thread.is_alive():
            self._switch_action(False)
            self._callback.reset()
        self.after(100, self.reset_buttons)

    def browse_directory(self):
        cur_dir = self._entry_folder.get()
        initial_dir = cur_dir if os.path.exists(cur_dir) else os.path.expanduser('~')
        directory = filedialog.askdirectory(title='Select directory',
                                            initialdir=initial_dir)
        if directory:
            self._entry_folder.delete(0, END)
            self._entry_folder.insert(0, directory)

    def _clean_text_box(self):
        try:
            self._text.configure(state=NORMAL)
            self._text.delete('1.0', END)
            self._text.configure(state=DISABLED)
        except TclError as exc:
            logging.warning('Can\'t clean text ({})'.format(exc))

    def _update_dl_with_fields(self):
        self._dl._url = self._entry_rss.get()
        self._dl.folder(self._entry_folder.get())
        self._dl.overwrite(self._overwrite.get() == 1)

    def _switch_action(self, action: bool):
        state_f_dl = DISABLED if action else NORMAL
        state_cancel = NORMAL if action else DISABLED
        self._btn_download.configure(state=state_f_dl)
        self._btn_fetch.configure(state=state_f_dl)
        self._btn_cancel.configure(state=state_cancel)

    def download(self):
        self._clean_text_box()
        self._update_dl_with_fields()
        logging.info("Start download")
        self._dl_thread = Thread(target=self._dl.download_mp3,
                                 kwargs={'cb': self._callback})
        self._switch_action(True)
        self._dl_thread.start()

    def fetch(self):
        self._clean_text_box()
        self._update_dl_with_fields()
        logging.info("Fetch info")
        self._fetch_thread = Thread(target=self._dl.list_mp3,
                                    kwargs={'verbose': True, 'cb': self._callback})
        self._switch_action(True)
        self._fetch_thread.start()

    def cancel(self):
        self._callback.cancel()
        logging.info('Action cancelled by user, waiting for threads to end...')
        if self._fetch_thread.is_alive():
            self._fetch_thread.join()
        if self._dl_thread.is_alive():
            self._dl_thread.join()
        self._callback.reset()
        self._switch_action(False)
        logging.info('Threads have ended')


class Log2Text(logging.Handler):
    def __init__(self, text):
        logging.Handler.__init__(self)
        self.setLevel(logging.INFO)
        f = logging.Formatter('[%(asctime)s][%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S')
        self.setFormatter(f)
        self._text = text

    def emit(self, record):
        formatted_message = self.format(record)
        self._text.configure(state=NORMAL)
        self._text.insert(END, formatted_message)
        self._text.insert(END, '\n')
        self._text.configure(state=DISABLED)
        self._text.see(END)


def main():
    root = Tk()
    icon_path = 'pbd_icon.ico'
    if not os.path.isfile(icon_path):
        icon_path = '../img/pbd_icon.ico'
    if os.path.isfile(icon_path):
        root.iconbitmap(icon_path)

    try:
        PDBApp(root)
        root.mainloop()
    except Exception as exc:
        show_message_box_on_exception(exc)
    return 0


if __name__ == '__main__':
    main()
