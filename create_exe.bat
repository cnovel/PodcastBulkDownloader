pyinstaller.exe --clean -F src\app.py -n PodcastBulkDownloader -i src/pbd_icon.ico --noconsole
pyinstaller.exe --clean -F src\bulk_downloader.py -n PodcastBulkDownloaderCLI -i src/pbd_icon.ico
copy src\pbd_icon.ico dist\pbd_icon.ico /y