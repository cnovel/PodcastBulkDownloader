from bs4 import BeautifulSoup
import requests
import os.path
import logging
import argparse
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

    expected_size = int(r.headers.get("content-length"))
    r.close()

    if cb and cb.is_cancelled():
        return False

    chunk_size = 2**20
    last_byte = 0
    with open(path, 'wb') as f:
        while last_byte < expected_size:
            if cb and cb.is_cancelled():
                return False
            logging.debug("{} vs {}".format(last_byte, expected_size))
            logging.debug("Starting download with already {}% of the file".
                          format((100*last_byte)/expected_size))
            resume_header = {'Range': 'bytes=%d-' % last_byte}
            resume_request = requests.get(url, headers=resume_header, stream=True,
                                          verify=True, allow_redirects=True)
            for data in resume_request.iter_content(chunk_size):
                last_byte += len(data)
                if cb and cb.is_cancelled():
                    return False
                if cb:
                    cb.progress(100 * (last_byte / expected_size))
                f.write(data)
            resume_request.close()
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
    while count < max_try:
        if download_with_resume(url, path, cb):
            return True
        count += 1
        sleep(sleep_time)
    logging.error('Download of {} failed after {} tries'.format(url, max_try))
    return False


class BulkDownloader:
    _EXT = '.mp3'

    def __init__(self, url: str, folder: str = None, overwrite: bool = True):
        """
        Constructor of the bulkdownloader
        @param url: URL of the RSS feed or web directory
        @param folder: Folder where to save the MP3s
        @param overwrite: Overwrite already downloaded files
        """
        self._url = url
        self._folder = folder
        self._overwrite = overwrite
        
    def overwrite(self, overwrite: bool = None) -> bool:
        """
        Set and return the overwrite parameter
        @param overwrite: New overwrite value
        @return: Overwrite value
        """
        if overwrite is not None:
            self._overwrite = overwrite
        return self._overwrite

    def folder(self, folder: str = None) -> str:
        """
        Set and return the save folder
        @param folder: New path of the folder
        @return: Folder path
        """
        if folder:
            self._folder = folder
        return self._folder

    def list_mp3(self, cb: Callback = None, verbose: bool = False) -> List[str]:
        """
        Will fetch the RSS or directory info and return the list of available MP3s
        @param cb: Callback object
        @param verbose: Outputs more logs
        @return: List of MP3 urls
        """
        try:
            r = requests.get(self._url)
        except requests.RequestException as exc:
            err_str = 'Failed to connect to URL ({})'.format(exc)
            logging.error(err_str)
            raise BulkDownloaderException(err_str)
        if r.status_code != 200:
            err_str = 'Failed to access URL (code {})'.format(r.status_code)
            logging.error(err_str)
            raise BulkDownloaderException(err_str)
        page = r.text
        if cb and cb.is_cancelled():
            return []
        if self._page_is_rss(page):
            logging.info('Processing RSS document')
            to_download = self._get_url_to_download_from_rss(page)
        else:
            logging.info('Processing HTML document')
            to_download = self._get_url_to_download_from_html(page)
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
        to_download = self.list_mp3(cb)
        logging.info('{} files will be downloaded'.format(len(to_download)))
        if cb:
            cb.progress(0)
        count = 0
        downloads_successful = 0
        downloads_skipped = 0
        nb_downloads = len(to_download)
        step = 100. / nb_downloads
        for file in to_download:
            if cb:
                if cb.is_cancelled():
                    return
                cb.progress(count * step)

            # Getting the name and path
            name = os.path.basename(file)
            name = name.replace('%20', ' ')
            path = os.path.join(self.folder(), name)

            # Check if we should skip the file
            if not self.overwrite() and os.path.isfile(path):
                logging.info('Skipping {} as the file already exists at {}'.format(name, path))
                downloads_skipped += 1
                count += 1
                continue

            # Download file
            logging.info('Saving {} to {} from {}'.format(name, path, file))
            if cb:
                cb.set_function(lambda x: (count + x / 100) * step)
            if not dry_run and try_download(file, path, cb=cb):
                downloads_successful += 1
            if cb:
                cb.set_function(lambda x: x)
            count += 1
        if cb:
            cb.progress(100)
        logging.info('{}/{} episodes were successfully downloaded'.format(downloads_successful,
                                                                          nb_downloads))
        logging.info('{}/{} episodes were skipped because files already existed'
                     .format(downloads_skipped, nb_downloads))

    def _get_url_to_download_from_html(self, page) -> List[str]:
        soup = BeautifulSoup(page, 'html.parser')
        return [self._url + '/' + node.get('href') for node in soup.find_all('a') if
                node.get('href').endswith(BulkDownloader._EXT)]

    @staticmethod
    def _get_url_to_download_from_rss(page):
        elem = ElementTree.XML(page)
        urls = BulkDownloader._get_mp3_urls_recursively(elem)
        return sorted(list(set(urls)))

    @staticmethod
    def _get_mp3_urls_recursively(root):
        urls = []
        for node in root:
            if 'url' in node.attrib and \
                    (node.attrib['url'].endswith(BulkDownloader._EXT) or
                     BulkDownloader._EXT + '?' in node.attrib['url']):
                urls.append(node.attrib['url'].replace('&amp;', '&'))
            urls += BulkDownloader._get_mp3_urls_recursively(node)

        return urls

    @staticmethod
    def _page_is_rss(page):
        try:
            return ElementTree.fromstring(page).tag == 'rss'
        except ElementTree.ParseError:
            return False


def download_mp3s(url: str, folder: str, overwrite: bool = True):
    """
    Will create a BulkDownloader and download all the mp3s from an URL to the folder
    @param url: Directory/RSS url
    @param folder: Where to save the MP3s
    @param overwrite: Overwrite existing files
    """
    logging.info('Downloading mp3s from {} to {}'.format(url, folder))
    if overwrite:
        logging.info('Already existing file will be overwritten')
    else:
        logging.info('Already existing file won\'t be overwritten')
    bulk_downloader = BulkDownloader(url, folder, overwrite)
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
    args = parser.parse_args()

    if args.version:
        return print_version()

    if not args.url or not args.folder:
        logging.error('You need to set both URL and FOLDER')
        return 1

    try:
        download_mp3s(args.url, args.folder, args.overwrite)
    except Exception as exc:
        logging.error(exc)
        return 1
    return 0


if __name__ == '__main__':
    main()
