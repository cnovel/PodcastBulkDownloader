import pytest
from .. import bulk_downloader as bd


def test_constructor():
    bdl = bd.BulkDownloader('https://feeds.radiokawa.com/podcast_nawak.xml', './dl')
    assert bdl._url == 'https://feeds.radiokawa.com/podcast_nawak.xml'
    assert bdl.folder() == './dl'


def test_set_folder():
    bdl = bd.BulkDownloader('https://feeds.radiokawa.com/podcast_nawak.xml', './dl')
    bdl.folder('./dl2')
    assert bdl.folder() == './dl2'


def test_list_mp3():
    bdl = bd.BulkDownloader('https://feeds.radiokawa.com/podcast_nawak.xml', './dl')
    assert len(bdl.list_mp3()) > 0


def test_wrong_feed():
    bdl = bd.BulkDownloader('https://feeds.radiokawa.com/podcast_nawak2.xml', './dl')
    with pytest.raises(bd.BulkDownloaderException):
        bdl.list_mp3()


def test_wrong_server():
    bdl = bd.BulkDownloader('https://feeds.radionawak.com/podcast_nawak2.xml', './dl')
    with pytest.raises(bd.BulkDownloaderException):
        bdl.list_mp3()

