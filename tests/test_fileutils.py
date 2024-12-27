from seeqret.fileutils import *


def test_appdata_dir():
    assert local_appdata_dir()
    assert roaming_appdata_dir()


def test_write_file():
    write_file('test-write-file.txt', """\
        hello world
    """)
    assert read_file('test-write-file.txt') == 'hello world\n'
    remove_file_if_exists('test-write-file.txt')


def test_read_json():
    write_file('test-read-json.json', """
        {
            "hello": "world"
        }
    """)
    assert read_json('test-read-json.json') == {"hello": "world"}
    remove_file_if_exists('test-read-json.json')
