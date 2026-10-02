"""`LanZouCloud` 公开 API 的正常路径/边界/失败路径回归测试。

对应 codex 审计 farfarfun/todo-list#671 的 finding 6：`upload_file`、
`upload_dir`、`down_file_by_url`、`down_dir_by_url`、移动、分享等公开 API
在 `tests/` 里原先没有任何覆盖。这里按方法补齐正常路径 + 边界 + 失败路径，
网络一律 mock，不发起真实请求。
"""

from __future__ import annotations

import os
from unittest import mock

from fundrives.lanzou import core

# --------------------------------------------------------------------- move_file


def test_move_file_returns_success_when_server_accepts():
    drive = core.LanZouCloud()
    resp = mock.Mock()
    resp.json.return_value = {"zt": 1}

    with mock.patch.object(drive, "_post", return_value=resp) as mocked_post:
        assert drive.move_file(1, 2) == core.LanZouCloud.SUCCESS

    assert mocked_post.call_args.args[1] == {"task": 20, "file_id": 1, "folder_id": 2}


def test_move_file_returns_failed_when_server_rejects():
    drive = core.LanZouCloud()
    resp = mock.Mock()
    resp.json.return_value = {"zt": 0}

    with mock.patch.object(drive, "_post", return_value=resp):
        assert drive.move_file(1, 2) == core.LanZouCloud.FAILED


def test_move_file_returns_network_error_when_post_fails():
    drive = core.LanZouCloud()
    with mock.patch.object(drive, "_post", return_value=None):
        assert drive.move_file(1, 2) == core.LanZouCloud.NETWORK_ERROR


# ----------------------------------------------------------------- get_share_info


def test_get_share_info_file_returns_share_details():
    drive = core.LanZouCloud()
    first = mock.Mock()
    first.json.return_value = {
        "info": {
            "f_id": "i123",
            "is_newd": "https://developer.lanzouv.com",
            "onof": "1",
            "pwd": "ab12",
        }
    }
    second = mock.Mock()
    second.json.return_value = {"text": "demo.zip", "info": "demo desc"}

    with mock.patch.object(drive, "_post", side_effect=[first, second]):
        info = drive.get_share_info(123, is_file=True)

    assert info.code == core.LanZouCloud.SUCCESS
    assert info.url == "https://developer.lanzouv.com/i123"
    assert info.name == "demo.zip"
    assert info.desc == "demo desc"
    assert info.pwd == "ab12"
    # 响应里的 is_newd 要被记为新的下载 host
    assert drive._host_url == "https://developer.lanzouv.com"


def test_get_share_info_folder_without_password():
    drive = core.LanZouCloud()
    resp = mock.Mock()
    resp.json.return_value = {
        "info": {
            "new_url": "https://developer.lanzouv.com/bxxx",
            "name": "我的文件夹",
            "des": "",
            "onof": "0",
        }
    }

    with mock.patch.object(drive, "_post", return_value=resp):
        info = drive.get_share_info(456, is_file=False)

    assert info.code == core.LanZouCloud.SUCCESS
    assert info.name == "我的文件夹"
    assert info.pwd == ""  # onof=0 时无提取码


def test_get_share_info_returns_id_error_for_invalid_folder():
    drive = core.LanZouCloud()
    resp = mock.Mock()
    resp.json.return_value = {"info": {"name": ""}}

    with mock.patch.object(drive, "_post", return_value=resp):
        info = drive.get_share_info(789, is_file=False)

    assert info.code == core.LanZouCloud.ID_ERROR


def test_get_share_info_returns_network_error_when_post_fails():
    drive = core.LanZouCloud()
    with mock.patch.object(drive, "_post", return_value=None):
        info = drive.get_share_info(1, is_file=True)

    assert info.code == core.LanZouCloud.NETWORK_ERROR


# ------------------------------------------------------------------- set_passwd


def test_set_passwd_file_enables_password():
    drive = core.LanZouCloud()
    resp = mock.Mock()
    resp.json.return_value = {"zt": 1}

    with mock.patch.object(drive, "_post", return_value=resp) as mocked_post:
        assert drive.set_passwd(1, "ab12", is_file=True) == core.LanZouCloud.SUCCESS

    assert mocked_post.call_args.args[1] == {
        "task": 23,
        "file_id": 1,
        "shows": 1,
        "shownames": "ab12",
    }


def test_set_passwd_folder_can_clear_password():
    drive = core.LanZouCloud()
    resp = mock.Mock()
    resp.json.return_value = {"zt": 1}

    with mock.patch.object(drive, "_post", return_value=resp) as mocked_post:
        assert drive.set_passwd(2, "", is_file=False) == core.LanZouCloud.SUCCESS

    assert mocked_post.call_args.args[1] == {
        "task": 16,
        "folder_id": 2,
        "shows": 0,
        "shownames": "",
    }


def test_set_passwd_returns_network_error_when_post_fails():
    drive = core.LanZouCloud()
    with mock.patch.object(drive, "_post", return_value=None):
        assert drive.set_passwd(1) == core.LanZouCloud.NETWORK_ERROR


# -------------------------------------------------------------------- upload_file


def test_upload_file_returns_path_error_for_missing_file(tmp_path):
    drive = core.LanZouCloud()
    missing = tmp_path / "missing.bin"
    task = mock.Mock()

    code, size, keep_going = drive.upload_file(task, str(missing))

    assert code == core.LanZouCloud.PATH_ERROR
    assert keep_going is True


def test_upload_file_returns_failed_for_empty_file(tmp_path):
    drive = core.LanZouCloud()
    empty = tmp_path / "empty.bin"
    empty.write_bytes(b"")
    task = mock.Mock()

    code, size, keep_going = drive.upload_file(task, str(empty))

    assert code == core.LanZouCloud.FAILED
    assert keep_going is False


def test_upload_file_rejects_big_file_when_not_allowed(tmp_path):
    drive = core.LanZouCloud()
    drive.set_max_size(1)  # 限制为 1 MB
    big = tmp_path / "big.bin"
    big.write_bytes(b"0" * (2 * 1024 * 1024))  # 2 MB，超过限制
    task = mock.Mock()

    code, size, keep_going = drive.upload_file(task, str(big), allow_big_file=False)

    assert code == core.LanZouCloud.OFFICIAL_LIMITED
    assert keep_going is False
    assert task.info == "文件大于1MB"


def test_upload_file_small_file_success(tmp_path):
    drive = core.LanZouCloud()
    small = tmp_path / "demo.txt"
    small.write_text("hello")
    task = mock.Mock()
    task.now_size = 0

    resp = mock.Mock(status_code=200)
    resp.json.return_value = {"zt": 1, "text": [{"id": "999"}]}

    with (
        mock.patch.object(drive, "_post", return_value=resp),
        mock.patch.object(
            drive, "set_passwd", return_value=core.LanZouCloud.SUCCESS
        ) as mocked_set_passwd,
    ):
        code, file_id, keep_going = drive.upload_file(task, str(small))

    assert code == core.LanZouCloud.SUCCESS
    assert file_id == 999
    assert keep_going is True
    mocked_set_passwd.assert_called_once_with("999")


def test_upload_file_small_file_network_error(tmp_path):
    drive = core.LanZouCloud()
    small = tmp_path / "demo.txt"
    small.write_text("hello")
    task = mock.Mock()
    task.now_size = 0

    with mock.patch.object(drive, "_post", return_value=None):
        code, file_id, keep_going = drive.upload_file(task, str(small))

    assert code == core.LanZouCloud.NETWORK_ERROR
    assert keep_going is True


def test_upload_file_small_file_server_rejects(tmp_path):
    drive = core.LanZouCloud()
    small = tmp_path / "demo.txt"
    small.write_text("hello")
    task = mock.Mock()
    task.now_size = 0

    resp = mock.Mock(status_code=200)
    resp.json.return_value = {"zt": 0}

    with mock.patch.object(drive, "_post", return_value=resp):
        code, file_id, keep_going = drive.upload_file(task, str(small))

    assert code == core.LanZouCloud.FAILED
    assert keep_going is True


# --------------------------------------------------------------------- upload_dir


def test_upload_dir_returns_path_error_when_not_a_directory(tmp_path):
    drive = core.LanZouCloud()
    task = mock.Mock()
    task.url = str(tmp_path / "missing_dir")

    code, folder_id, keep_going = drive.upload_dir(task, callback=None)

    assert code == core.LanZouCloud.PATH_ERROR
    assert task.info == core.LanZouCloud.PATH_ERROR


def test_upload_dir_returns_mkdir_error_when_mkdir_fails(tmp_path):
    drive = core.LanZouCloud()
    task = mock.Mock()
    task.url = str(tmp_path)
    task.fid = -1

    with mock.patch.object(drive, "mkdir", return_value=core.LanZouCloud.MKDIR_ERROR):
        code, folder_id, keep_going = drive.upload_dir(task, callback=None)

    assert code == core.LanZouCloud.MKDIR_ERROR
    assert task.info == core.LanZouCloud.MKDIR_ERROR


def test_upload_dir_uploads_every_file_and_skips_subdirectories(tmp_path):
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "b.txt").write_text("b")
    (tmp_path / "subdir").mkdir()

    drive = core.LanZouCloud()
    task = mock.Mock()
    task.url = str(tmp_path)
    task.fid = -1

    with (
        mock.patch.object(drive, "mkdir", return_value=42),
        mock.patch.object(
            drive, "upload_file", return_value=(core.LanZouCloud.SUCCESS, 1, True)
        ) as mocked_upload,
    ):
        code, folder_id, keep_going = drive.upload_dir(task, callback=None)

    assert code == core.LanZouCloud.SUCCESS
    assert folder_id == 42
    assert mocked_upload.call_count == 2
    uploaded_paths = {call.args[1] for call in mocked_upload.call_args_list}
    assert uploaded_paths == {
        str(tmp_path / "a.txt"),
        str(tmp_path / "b.txt"),
    }


# ---------------------------------------------------------------- down_file_by_url


def test_down_file_by_url_returns_url_invalid_for_folder_url():
    drive = core.LanZouCloud()
    task = mock.Mock()

    with mock.patch.object(core, "is_file_url", return_value=False):
        code = drive.down_file_by_url(
            "https://demo.lanzoub.com/bxxxx", task, callback=lambda: None
        )

    assert code == core.LanZouCloud.URL_INVALID
    assert task.info == core.LanZouCloud.URL_INVALID


def test_down_file_by_url_propagates_durl_failure(tmp_path):
    drive = core.LanZouCloud()
    task = mock.Mock()
    task.path = str(tmp_path)

    with (
        mock.patch.object(core, "is_file_url", return_value=True),
        mock.patch.object(
            drive,
            "get_durl_by_url",
            return_value=core.DirectUrlInfo(core.LanZouCloud.PASSWORD_ERROR, "", ""),
        ),
    ):
        code = drive.down_file_by_url(
            "https://demo.lanzoub.com/ixxxx", task, callback=lambda: None
        )

    assert code == core.LanZouCloud.PASSWORD_ERROR
    assert task.info == core.LanZouCloud.PASSWORD_ERROR


def test_down_file_by_url_downloads_full_file(tmp_path):
    drive = core.LanZouCloud()
    task = mock.Mock()
    task.path = str(tmp_path)
    task.pwd = ""
    task.url = "https://demo.lanzoub.com/ixxxx"
    task.now_size = 0

    head_resp = mock.Mock(headers={"Content-Length": "5"})
    get_resp = mock.Mock(status_code=200)
    get_resp.iter_content.return_value = [b"hello"]

    with (
        mock.patch.object(core, "is_file_url", return_value=True),
        mock.patch.object(
            drive,
            "get_durl_by_url",
            return_value=core.DirectUrlInfo(
                core.LanZouCloud.SUCCESS, "demo.txt", "https://durl.example/demo.txt"
            ),
        ),
        mock.patch.object(drive, "_head", return_value=head_resp),
        mock.patch.object(drive, "_get", return_value=get_resp),
    ):
        code = drive.down_file_by_url(task.url, task, lambda: None)

    assert code == core.LanZouCloud.SUCCESS
    saved = tmp_path / "demo.txt"
    assert saved.read_bytes() == b"hello"
    assert task.now_size == 5


# ----------------------------------------------------------------- down_dir_by_url


def test_down_dir_by_url_propagates_folder_detail_failure():
    drive = core.LanZouCloud()
    task = mock.Mock()

    with mock.patch.object(
        drive,
        "get_folder_info_by_url",
        return_value=core.FolderDetail(core.LanZouCloud.PASSWORD_ERROR),
    ):
        code = drive.down_dir_by_url(task, callback=lambda: None)

    assert code == core.LanZouCloud.PASSWORD_ERROR
    assert task.info == core.LanZouCloud.PASSWORD_ERROR


def test_down_dir_by_url_downloads_each_file_in_folder(tmp_path):
    drive = core.LanZouCloud()
    task = mock.Mock()
    task.path = str(tmp_path)
    task.pwd = ""
    task.url = "https://demo.lanzoub.com/bxxxx"

    file_a = core.FileInFolder(
        name="a.txt",
        time="",
        size="1 K",
        type="txt",
        url="https://demo.lanzoub.com/ia",
        pwd="",
    )
    file_b = core.FileInFolder(
        name="b.txt",
        time="",
        size="1 K",
        type="txt",
        url="https://demo.lanzoub.com/ib",
        pwd="",
    )
    folder_info = core.FolderInfo(
        name="演示文件夹",
        id="1",
        pwd="",
        time="",
        desc="",
        url="",
        size="2 K",
        size_int=2048,
        count=2,
    )
    detail = core.FolderDetail(
        core.LanZouCloud.SUCCESS, folder_info, [file_a, file_b], []
    )

    with (
        mock.patch.object(drive, "get_folder_info_by_url", return_value=detail),
        mock.patch.object(drive, "_check_big_file", return_value=None),
        mock.patch.object(
            drive, "down_file_by_url", return_value=core.LanZouCloud.SUCCESS
        ) as mocked_down,
    ):
        code = drive.down_dir_by_url(task, callback=lambda: None)

    assert code == core.LanZouCloud.SUCCESS
    assert mocked_down.call_count == 2
    downloaded_urls = {call.args[0] for call in mocked_down.call_args_list}
    assert downloaded_urls == {file_a.url, file_b.url}
    assert os.path.isdir(os.path.join(str(tmp_path), "演示文件夹"))
