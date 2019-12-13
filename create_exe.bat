pyinstaller.exe --clean -F src\app.py -n PodcastBulkDownloader -i img/pbd_icon.ico --noconsole
pyinstaller.exe --clean -F src\bulk_downloader.py -n PodcastBulkDownloaderCLI -i img/pbd_icon.ico
copy img\pbd_icon.ico dist\pbd_icon.ico /y