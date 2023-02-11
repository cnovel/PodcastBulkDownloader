import datetime
import requests
import os.path
import logging
import argparse
import re
from pyPodcastParser.Podcast import Podcast
from enum import Enum
from src.callback import Callback
from time import sleep
from xml.etree import ElementTree
from typing import List
from src import pbd_version


class BulkDownloaderException(Exception):
    pass


def download_with_resume(url: str, path: str, cb: Callback = None) -> bool:
    """
    Download a file pointed by url to a local path
    @param url: URL to download
    @param path: Local file to be saved
    @param cb: Callback object
    @return: True if the file was completely downloaded
    """
    logging.debug("Downloading {} to {}".format(url, path))

    # Clean existing file
    if os.path.exists(path):
        os.remove(path)

    if cb and cb.is_cancelled():
        return False

    try:
        r = requests.head(url, allow_redirects=True)
    except requests.exceptions as e:
        logging.error(e)
        return False

    if r.status_code < 200 or r.status_code > 302:
        logging.error("Failed to reach {}, status is {}".format(url, r.status_code))
        r.close()
        return False
    expected_size = 0
    if "content-length" in r.headers.keys():
        expected_size = int(r.headers.get("content-length"))
    r.close()

    if cb and cb.is_cancelled():
        return False

    chunk_size = 2**20
    last_byte = 0
    transfer_is_over = False
    with open(path, 'wb') as f:
        while not transfer_is_over:
            if cb and cb.is_cancelled():
                return False
            resume_header = {'Range': 'bytes=%d-' % last_byte}
            resume_request = requests.get(url, headers=resume_header, stream=True,
                                          verify=True, allow_redirects=True)
            for data in resume_request.iter_content(chunk_size):
                last_byte += len(data)
                if cb and cb.is_cancelled():
                    return False
                if cb and expected_size > 0:
                    cb.progress(100 * (last_byte / expected_size))
                f.write(data)
                if len(data) < chunk_size:
                    transfer_is_over = True
            resume_request.close()
    if cb and cb.is_cancelled():
        return False
    if cb:
        cb.progress(100)
    return True


def try_download(url, path, max_try=3, sleep_time=5, cb: Callback = None) -> bool:
    """
    Try to download the file multiple times, in case of connection failures
    @param url: URL to download
    @param path: Local file to be saved
    @param max_try: Number of download tries
    @param sleep_time: Wait time between tries in second
    @param cb: Callback object
    @return: True if the file was completely downloaded
    """
    count = 0
    try:
        while count < max_try:
            if download_with_resume(url, path, cb):
                return True
            if cb and cb.is_cancelled():
                return False
            count += 1
            sleep(sleep_time)
        logging.error('Download of {} failed after {} tries'.format(url, max_try))
        return False
    except Exception as exc:
        logging.error('Download of {} crashed: {}'.format(url, max_try, exc))
        return False


class Prefix(Enum):
    """
    Indicate which prefix to use
    """
    NO_PREFIX = 1
    DATE = 2
    DATE_TIME = 3

    def __str__(self):
        return self.name

    @staticmethod
    def from_string(s):
        try:
            return Prefix[s]
        except KeyError:
            raise ValueError()


class Episode:
    def __init__(self, url: str, title: str, date_time: datetime.datetime):
        """
        Constructor for a podcast episode
        @param url: URL of the MP3 file
        @param title: Title of the episode
        @param date_time: Date time of the episode
        """
        self._url = url
        self._title = title
        self._date_time = date_time

    def title(self, title: str = None) -> str:
        if title is not None:
            self._title = title
        return self._title

    def url(self) -> str:
        return self._url

    def safe_title(self) -> str:
        """
        Returns a title that can be saved on disk
        """
        no_invalid = re.sub(r'[\\/:"*?<>|]+', '', self.title())
        return re.sub(' +', ' ', no_invalid).strip()

    def get_date_time(self) -> datetime.datetime:
        return self._date_time

    def get_filename(self, prefix: Prefix) -> str:
        filename = self.safe_title() + '.mp3'
        if prefix == Prefix.DATE:
            filename = self.get_date_time().date().isoformat() + ' ' + filename
        elif prefix == Prefix.DATE_TIME:
            filename = self.get_date_time().isoformat('_').replace(':', '-') + ' ' + filename
        return filename

    def __str__(self) -> str:
        return 'Episode "{}" ({})'.format(self.title(), self.url())


class BulkDownloader:
    _EXT = '.mp3'

    def __init__(self, url: str, folder: str = None, last_n: int = 0, overwrite: bool = True,
                 prefix: Prefix = Prefix.NO_PREFIX):
        """
        Constructor of the bulkdownloader
        @param url: URL of the RSS feed or web directory
        @param folder: Folder where to save the MP3s
        @param last_n: Only download the last N episodes, all if N = 0
        @param overwrite: Overwrite already downloaded files
        @param prefix: Prefix added for each file name
        """
        self._url = url
        self._folder = folder
        self._last_n = last_n
        self._overwrite = overwrite
        self._prefix = prefix

    def last_n(self, n: int = None):
        """
        Set and return the last_n parameter
        @param n: New last_n value
        @return: last_n value
        """
        if n is not None:
            self._last_n = n
        return self._last_n

    def overwrite(self, overwrite: bool = None) -> bool:
        """
        Set and return the overwrite parameter
        @param overwrite: New overwrite value
        @return: Overwrite value
        """
        if overwrite is not None:
            self._overwrite = overwrite
        return self._overwrite

    def prefix(self, prefix: Prefix = None) -> Prefix:
        """
        Set and return the prefix with datetime parameter
        @param prefix: New prefix value
        @return: Prefix value
        """
        if prefix is not None:
            self._prefix = prefix
        return self._prefix

    def folder(self, folder: str = None) -> str:
        """
        Set and return the save folder
        @param folder: New path of the folder
        @return: Folder path
        """
        if folder:
            self._folder = folder
        return self._folder

    def list_mp3(self, cb: Callback = None, verbose: bool = False) -> List[Episode]:
        """
        Will fetch the RSS or directory info and return the list of available MP3s
        @param cb: Callback object
        @param verbose: Outputs more logs
        @return: List of MP3 urls
        """
        try:
            headers = {'Accept': '*/*',
                       'User-Agent': 'PodcastBulkDownloader v' + pbd_version}
            r = requests.get(self._url, headers=headers)
        except requests.RequestException as exc:
            err_str = 'Failed to connect to URL ({})'.format(exc)
            logging.error(err_str)
            raise BulkDownloaderException(err_str)
        if r.status_code != 200:
            err_str = 'Failed to access URL (code {})'.format(r.status_code)
            logging.error(err_str)
            raise BulkDownloaderException(err_str)
        page = r.content
        if cb and cb.is_cancelled():
            return []
        if self._page_is_rss(page):
            logging.info('Processing RSS document')
            to_download = self._get_episodes_to_download_from_rss(page)
            # We trim the list if needed
            if 0 < self._last_n < len(to_download):
                to_download = to_download[0:self._last_n]
        else:
            err_str = 'Content is not RSS'
            logging.error(err_str)
            raise BulkDownloaderException(err_str)
        if cb and cb.is_cancelled():
            return []
        if verbose:
            logging.info('{} episodes found in the feed:'.format(len(to_download)))
            for elem in to_download:
                logging.info(elem)
        return to_download

    def download_mp3(self, cb: Callback = None, dry_run: bool = False):
        """
        Will get the list of MP3s and download them into the specified folder
        @param cb: Callback object
        @param dry_run: Will not actually download anythin (for test purposes only)
        @return: None
        """
        if not self.folder():
            err_str = 'No folder is defined for the download'
            logging.error(err_str)
            raise BulkDownloaderException(err_str)

        if len(self.folder()) > 240:
            err_str = 'Folder name is too long, please chose a shorter folder name'
            logging.error(err_str)
            raise BulkDownloaderException(err_str)

        to_download = self.list_mp3(cb)
        logging.info('{} files will be downloaded'.format(len(to_download)))
        if cb and cb.is_cancelled():
            return
        if cb:
            cb.progress(0)
        count = 0
        downloads_successful = 0
        downloads_skipped = 0
        nb_downloads = len(to_download)
        step = 100. / nb_downloads
        for episode in to_download:
            if cb:
                if cb.is_cancelled():
                    continue
                cb.progress(count * step)

            # Getting the name and path
            name = episode.get_filename(self.prefix())
            path = os.path.normpath(os.path.join(self.folder(), name))
            if len(path) >= 260:
                short_path = path[:-3][0:256] + ".mp3"
                logging.warning(f"{path} is too long shortening to {short_path}")
                path = short_path

            # Check if we should skip the file
            if not self.overwrite() and os.path.isfile(path):
                logging.info('Skipping {} as the file already exists at {}'
                             .format(name, path))
                downloads_skipped += 1
                count += 1
                continue

            # Download file
            logging.info('Saving {} to {} from {}'.format(name, path, episode.url()))
            if cb:
                cb.set_function(lambda x: (count + x / 100) * step)
            if not dry_run and try_download(episode.url(), path, cb=cb):
                downloads_successful += 1
            if cb:
                cb.set_function(lambda x: x)
            count += 1

        if cb and cb.is_cancelled():
            return

        if cb:
            cb.progress(100)
        logging.info('{}/{} episodes were successfully downloaded'.format(downloads_successful,
                                                                          nb_downloads))
        logging.info('{}/{} episodes were skipped because files already existed'
                     .format(downloads_skipped, nb_downloads))

    @staticmethod
    def _get_episodes_to_download_from_rss(page) -> List[Episode]:
        episodes = []
        pod_feed = Podcast(page)
        for item in pod_feed.items:
            pub_date_time = datetime.datetime.utcfromtimestamp(item.time_published) \
                if item.time_published > 0 else item.published_date
            episodes.append(Episode(item.enclosure_url, item.title, pub_date_time))
        return episodes

    @staticmethod
    def _page_is_rss(page):
        try:
            return ElementTree.fromstring(page).tag == 'rss'
        except ElementTree.ParseError as error:
            logging.error("Failed to parse XML: {}".format(error))
            return False


def download_mp3s(url: str, folder: str, last_n: int, overwrite: bool = True, prefix: Prefix = Prefix.NO_PREFIX):
    """
    Will create a BulkDownloader and download all the mp3s from an URL to the folder
    @param url: Directory/RSS url
    @param folder: Where to save the MP3s
    @param last_n: Only download the last N episodes, all if N = 0
    @param overwrite: Overwrite existing files
    @param prefix: Prefix type for each file
    """
    logging.info('Downloading mp3s from {} to {}'.format(url, folder))
    if overwrite:
        logging.info('Already existing file will be overwritten')
    else:
        logging.info('Already existing file won\'t be overwritten')
    bulk_downloader = BulkDownloader(url, folder, last_n, overwrite, prefix)
    bulk_downloader.download_mp3()


def print_version() -> int:
    print(pbd_version)
    return 0


def main() -> int:
    """
    Main function for CLI
    @return: Int exit code
    """
    logging.getLogger().setLevel(logging.INFO)
    log_format = "[%(levelname)s] %(message)s"
    logging.basicConfig(format=log_format)
    logging.captureWarnings(True)
    parser = argparse.ArgumentParser(description='Download MP3s from RSS feed or web folder')
    parser.add_argument('--url', dest='url', help='URL to inspect for MP3s')
    parser.add_argument('-f', '--folder', dest='folder',
                        help='Destination folder for MP3 files')
    parser.add_argument('--overwrite', dest='overwrite', action='store_true',
                        help='Will overwrite existing files')
    parser.add_argument('-v', '--version', dest='version', action='store_true',
                        help='Print version')
    parser.add_argument('-l', '--last', dest='last_n', default=0,
                        help='Only download the last N episodes, if N=0, download all the episodes')
    parser.add_argument('--prefix', dest='prefix', type=Prefix.from_string, choices=list(Prefix),
                        default=Prefix.NO_PREFIX, help='Prefix for the filename')
    args = parser.parse_args()

    if args.version:
        return print_version()

    if not args.url or not args.folder:
        logging.error('You need to set both URL and FOLDER')
        return 1

    try:
        download_mp3s(args.url, args.folder, int(args.last_n), args.overwrite, args.prefix)
    except Exception as exc:
        logging.error(exc)
        return 1
    return 0


if __name__ == '__main__':
    main()
