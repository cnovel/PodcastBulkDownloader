from bs4 import BeautifulSoup
import requests
import os.path
import urllib
import logging
import argparse
from xml.etree import ElementTree


class BulkDownloaderException(Exception):
    pass


class BulkDownloader:
    _EXT = '.mp3'

    def __init__(self, url: str, folder: str = None):
        self._url = url
        self._folder = folder

    def folder(self, folder: str = None):
        if folder:
            self._folder = folder
        return self._folder

    def list_mp3(self):
        try:
            r = requests.get(self._url)
        except requests.RequestException as exc:
            raise BulkDownloaderException('Failed to connect to URL ({})'.format(exc))
        if r.status_code != 200:
            raise BulkDownloaderException('Failed to access URL (code {})'.format(r.status_code))
        page = r.text
        if self._page_is_rss(page):
            logging.info('Processing RSS document')
            to_download = self._get_url_to_download_from_rss(page)
        else:
            logging.info('Processing HTML document')
            to_download = self._get_url_to_download_from_html(page)
        return to_download

    def download_mp3(self):
        if not self.folder():
            raise BulkDownloaderException('No folder is defined for the download')
        to_download = self.list_mp3()
        logging.info('{} files will be downloaded'.format(len(to_download)))
        for file in to_download:
            name = os.path.basename(file)
            name = name.replace('%20', ' ')
            path = os.path.join(self.folder(), name)
            logging.info('Saving {} to {}'.format(name, path))
            urllib.request.urlretrieve(file, path)
            logging.info('Done')

    def _get_url_to_download_from_html(self, page):
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


def download_mp3s(url, folder):
    logging.info('Downloading mp3s from {} to {}'.format(url, folder))
    bulk_downloader = BulkDownloader(url, folder)
    bulk_downloader.download_mp3()


def main():
    logging.getLogger().setLevel(logging.INFO)
    log_format = "[%(levelname)s] %(message)s"
    logging.basicConfig(format=log_format)
    parser = argparse.ArgumentParser(description='Download MP3s from RSS feed or web folder')
    parser.add_argument('--url', dest='url', help='URL to inspect')
    parser.add_argument('-f', '--folder', dest='folder', help='Destination folder')
    args = parser.parse_args()

    try:
        download_mp3s(args.url, args.folder)
    except Exception as exc:
        logging.error(exc)
        return 1
    return 0


if __name__ == '__main__':
    main()
