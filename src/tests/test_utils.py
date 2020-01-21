from src import utils
from os.path import join


def test_path_at_level():
    p = 'https://media.acast.com/qommute/episode-4-lamarcheapied/media.mp3'
    assert 'media.mp3' == utils.get_path_at_level(p, 0)
    assert join('episode-4-lamarcheapied', 'media.mp3') == utils.get_path_at_level(p, 1)


def test_unique_names():
    unique_names = utils.get_unique_names(['https://media.acast.com/qommute/episode-4-lamarcheapied/media.mp3',
                                           'https://media.acast.com/qommute/episode-3-bus/media.mp3'])
    assert 'episode-4-lamarcheapied_media.mp3' == unique_names[0][1]
    assert 'episode-3-bus_media.mp3' == unique_names[1][1]


def test_unique():
    names = ['a', 'a', 'b']
    assert not utils.names_are_unique(names)
    names = ['a', 'b', 'c']
    assert utils.names_are_unique(names)


def test_exclude_params():
    n = utils.exclude_params('BNApPcKkPlOj.mp3?t=1579538694')
    assert 'BNApPcKkPlOj.mp3' == n
    n = utils.exclude_params('BNApPcKkPlOj.mp3')
    assert 'BNApPcKkPlOj.mp3' == n
