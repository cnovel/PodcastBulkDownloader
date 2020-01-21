![PBD_Logo](img/pdb_logo_small.png)

# Podcast Bulk Downloader
[![Build Status](https://travis-ci.org/cnovel/PodcastBulkDownloader.svg?branch=master)](https://travis-ci.org/cnovel/PodcastBulkDownloader) [![codecov](https://codecov.io/gh/cnovel/PodcastBulkDownloader/branch/master/graph/badge.svg)](https://codecov.io/gh/cnovel/PodcastBulkDownloader)

**Podcast Bulk Downloader** is a simple soft that allows you to download all the episodes of a podcast feed in a folder.

## How to use Podcast Bulk Downloader
### CLI version
Usage: `PodcastBulkDownloaderCLI.exe -f FOLDER --url RSS_URL [--overwrite]`

Arguments:
* `-h`, `--help`: shows this help message and exit
* `--url URL`: URL to inspect for MP3s
* `-f FOLDER`, `--folder FOLDER`: Destination folder for MP3 files
* `--overwrite`: Will overwrite existing files
* `version`: Print version

Example:
```
PodcastBulkDownloaderCLI.exe -f "G:\Musique\RadioKawa\Ta Gueule" --url https://feeds.radiokawa.com/podcast_ta-gueule.xml
```

### GUI Version
![PBD_GUI](img/PBD_GUI.png)

It's fairly easy to use: fill the RSS field, click Fetch to inspect the feed.
Then fill the Folder field and click download to download the episodes.
Logs will be displayed in the bottom part and will warn you if the software ran into issues.
Check the overwrite checkbox if you want to redownload all the episodes.
Overwriting is solely based on filename, it doesn't do any checks at the moment.

## How to build _PBD_
### Build and run tests
We are supporting Python 3.7 and above. Project may work for earlier version tough it is not guaranteed.

To install dependencies, execute this command in the root folder:
```
pip install .
```

To run tests, execute this command in the root folder:
```
pytest -v
```

### Creating EXE file
Execute `create_exe.bat`, it will create the exe files in a subdirectory called `dist`.
