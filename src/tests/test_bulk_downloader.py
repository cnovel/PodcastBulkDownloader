import datetime

import pytest
import os
import sys
from shutil import rmtree
from src import bulk_downloader as bd
from src.callback import Callback
from unittest.mock import patch


def test_constructor():
    bdl = bd.BulkDownloader('https://feeds.radiokawa.com/podcast_nawak.xml', './dl', 0, False)
    assert bdl._url == 'https://feeds.radiokawa.com/podcast_nawak.xml'
    assert bdl.folder() == './dl'
    assert not bdl.overwrite()


def test_set_folder():
    bdl = bd.BulkDownloader('https://feeds.radiokawa.com/podcast_nawak.xml', './dl')
    bdl.folder('./dl2')
    assert bdl.folder() == './dl2'


def test_set_overwrite():
    bdl = bd.BulkDownloader('https://feeds.radiokawa.com/podcast_nawak.xml', './dl', 0, False)
    assert not bdl.overwrite()
    bdl.overwrite(True)
    assert bdl.overwrite()
    bdl.overwrite(False)
    assert not bdl.overwrite()


def test_set_last_n():
    bdl = bd.BulkDownloader('https://feeds.radiokawa.com/podcast_nawak.xml', './dl', 2)
    assert bdl.last_n() == 2
    bdl.last_n(10)
    assert bdl.last_n() == 10


def test_list_mp3():
    bdl = bd.BulkDownloader('https://feeds.radiokawa.com/podcast_nawak.xml', './dl')
    cb = Callback()
    assert len(bdl.list_mp3(cb, True)) > 0


def test_list_mp3_limited():
    bdl = bd.BulkDownloader('https://feeds.radiokawa.com/podcast_nawak.xml', './dl', 2)
    cb = Callback()
    assert len(bdl.list_mp3(cb, True)) == 2


def test_wrong_feed():
    bdl = bd.BulkDownloader('https://feeds.radiokawa.com/podcast_nawak2.xml', './dl')
    with pytest.raises(bd.BulkDownloaderException):
        bdl.list_mp3()


def test_wrong_server():
    bdl = bd.BulkDownloader('https://feeds.radionawak.com/podcast_nawak2.xml', './dl')
    with pytest.raises(bd.BulkDownloaderException):
        bdl.list_mp3()


def test_dl_no_folder():
    bdl = bd.BulkDownloader('https://feeds.radiokawa.com/podcast_nawak.xml')
    assert len(bdl.list_mp3()) > 0
    with pytest.raises(bd.BulkDownloaderException):
        bdl.download_mp3()


def test_dl_dry():
    bdl = bd.BulkDownloader('https://feeds.radiokawa.com/podcast_nawak.xml', './dl')
    assert len(bdl.list_mp3()) > 0
    cb = Callback()
    bdl.download_mp3(dry_run=True, cb=cb)


def test_dl_dry_cancel():
    bdl = bd.BulkDownloader('https://feeds.radiokawa.com/podcast_nawak.xml', './dl')
    assert len(bdl.list_mp3()) > 0
    cb = Callback()
    cb.cancel()
    bdl.download_mp3(dry_run=True, cb=cb)


def test_dl_dry_no_cb():
    bdl = bd.BulkDownloader('https://feeds.radiokawa.com/podcast_nawak.xml', './dl')
    assert len(bdl.list_mp3()) > 0
    bdl.download_mp3(dry_run=True)


def test_main_with_version():
    args = ['script', '--version']
    with patch.object(sys, 'argv', args):
        res = bd.main()
        assert res == 0


@pytest.fixture(scope='module')
def tmp_directory(request):
    tmp_directory = os.path.join(os.getcwd(), 'tmp_dir')
    if os.path.exists(tmp_directory):
        rmtree(tmp_directory)
    os.mkdir(tmp_directory)

    def clean():
        rmtree(tmp_directory)
    request.addfinalizer(clean)
    return tmp_directory


def test_try_download_ok(tmp_directory):
    cb = Callback()
    assert bd.try_download('http://xerto.free.fr/newban.jpg',
                           os.path.join(tmp_directory, 'newban.jpg'), 2, 1, cb)


def test_try_download_ko(tmp_directory):
    assert not bd.try_download('http://xerto.free.fr/pouet.jpg',
                               os.path.join(tmp_directory, 'pouet.jpg'), 2, 1)


def test_try_download_cancel(tmp_directory):
    cb = Callback()
    cb.cancel()
    assert not bd.try_download('https://feeds.radiokawa.com/podcast_nawak.xml',
                               os.path.join(tmp_directory, 't.xml'), 1, 1, cb)


def test_dl_dry_files_exist(tmp_directory):
    bdl = bd.BulkDownloader('https://feeds.radiokawa.com/podcast_nawak.xml', tmp_directory, False)
    open(os.path.join(tmp_directory, "NAWAK1.mp3"), "w")
    bdl.download_mp3(None, True)


def test_episode():
    dt = datetime.datetime.utcnow()
    ep1 = bd.Episode('https://www.podtrac.com/pts/redirect.mp3/dl.radiokawa.com/nawak/NAWAK7.mp3', 'Nawak 7', dt)
    assert ep1.title() == 'Nawak 7'
    assert ep1.title("Nawak 7 avec Yann")
    assert ep1.safe_title() == 'Nawak 7 avec Yann'
    assert ep1.url() == 'https://www.podtrac.com/pts/redirect.mp3/dl.radiokawa.com/nawak/NAWAK7.mp3'
    assert ep1.get_filename(bd.Prefix.NO_PREFIX) == "Nawak 7 avec Yann.mp3"
    assert ep1.get_filename(bd.Prefix.DATE) == dt.date().isoformat() + " Nawak 7 avec Yann.mp3"
    assert ep1.get_filename(bd.Prefix.DATE_TIME) == dt.isoformat('_').replace(':', '-') + " Nawak 7 avec Yann.mp3"

    ep2 = bd.Episode('https://www.podtrac.com/pts/redirect.mp3/dl.radiokawa.com/nawak/NAWAK6.mp3',
                     'Nawak 6 : Qu\'est-ce qu\'on fait demain ?', dt)
    assert ep2.get_filename(bd.Prefix.NO_PREFIX) == 'Nawak 6 Qu\'est-ce qu\'on fait demain.mp3'


def test_prefix_enum():
    p = bd.Prefix.from_string("NO_PREFIX")
    assert p == bd.Prefix.NO_PREFIX
    with pytest.raises(ValueError):
        bd.Prefix.from_string("WRONG")


def test_rss_parse_error():
    assert not bd.BulkDownloader._page_is_rss("This is not xml".encode('utf-8'))
