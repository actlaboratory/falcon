# -*- coding: utf-8 -*-
# Falcon archiver
# Note: All comments except these top lines will be written in Japanese.

"""
ファイルの圧縮と解凍の処理。画面には依存しない。

- ZIP と TAR 系（tar / tar.gz / tar.bz2 / tar.xz）、単独の gz / bz2 / xz は falcon だけで扱う
- 7z の圧縮、パスワード付きの圧縮、7z / RAR / LZH などの解凍は、同梱の 7-Zip（bin/7z.exe）を使う。
  利用者がインストールした 7-Zip は、版の違いによる不具合を見つけにくくなるので使わない
- 圧縮は保存先の一時フォルダに、解凍は展開先の一時フォルダに行い、最後に本来の名前へ移す。
  途中で失敗・中止しても、作りかけのファイルは残さない
"""

import bz2
import gzip
import logging
import lzma
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import zipfile
import zlib

log = logging.getLogger("falcon.archiver")

# 解凍先に同じ名前のファイルがあるときの動作
CONFLICT_RENAME = "rename"
CONFLICT_SKIP = "skip"
CONFLICT_OVERWRITE = "overwrite"

_CHUNK_SIZE = 256 * 1024
_TEMP_PREFIX = "~falcon"
_MAX_MESSAGE_LINES = 10

# 同梱の 7-Zip。exe では falcon.exe、開発時はこのファイルと同じ場所の bin フォルダにある
_APP_DIRECTORY = os.path.dirname(os.path.abspath(sys.executable if hasattr(sys, "frozen") else __file__))
SEVEN_ZIP_PATH = os.path.join(_APP_DIRECTORY, "bin", "7z.exe")

_TAR_MODES = {".tar": "w", ".tar.gz": "w:gz", ".tar.bz2": "w:bz2", ".tar.xz": "w:xz"}
_TAR_EXTENSIONS = (".tar.gz", ".tar.bz2", ".tar.xz", ".tgz", ".tbz2", ".tbz", ".txz", ".tar")
_SINGLE_OPENERS = {".gz": gzip.open, ".bz2": bz2.open, ".xz": lzma.open}
_SEVEN_ZIP_EXTENSIONS = (
    ".7z", ".rar", ".lzh", ".lha", ".cab", ".iso", ".arj", ".wim", ".z", ".zst", ".lzma", ".cpio", ".rpm", ".deb")
_ZIP_METHODS = (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED, zipfile.ZIP_BZIP2, zipfile.ZIP_LZMA)

# Windows で使えない文字と、予約された名前
_INVALID_CHARS = re.compile(r"[\x00-\x1f:*?\"<>|]")
_RESERVED_NAMES = re.compile(r"^(con|prn|aux|nul|com[0-9]|lpt[0-9])\s*(\.|$)", re.IGNORECASE)
_PASSWORD_ERROR = re.compile(r"wrong password|enter password", re.IGNORECASE)


class ArchiveError(Exception):
    """圧縮・解凍の失敗。メッセージはそのまま利用者に見せる。"""


class PasswordError(ArchiveError):
    """パスワードが必要、またはパスワードが違う"""


class Canceled(Exception):
    """利用者が中止した"""


class CompressFormat:
    """圧縮の形式"""

    def __init__(self, extension: str, name: str, needs_seven_zip: bool = False, supports_password: bool = False):
        self.extension = extension
        self.name = name
        self.needs_seven_zip = needs_seven_zip
        self.supports_password = supports_password


class CompressRequest:
    """圧縮する内容"""

    def __init__(self, sources: list, destination: str, archive_format: CompressFormat, password: str = ""):
        # 圧縮するファイル・フォルダのフルパス。すべて同じフォルダにあること
        self.sources = sources
        # 作成する書庫のフルパス
        self.destination = destination
        self.archive_format = archive_format
        self.password = password


class ExtractRequest:
    """解凍する内容"""

    def __init__(self, directory: str, make_folder: bool, conflict: str):
        # 展開先のフォルダ
        self.directory = directory
        # 書庫の名前のフォルダを作って展開するか
        self.make_folder = make_folder
        # CONFLICT_*
        self.conflict = conflict

    def get_directory(self, archive: str):
        """指定した書庫の展開先のフォルダを返す"""
        if not self.make_folder:
            return self.directory
        path = os.path.join(self.directory, _safe_name(get_stem(archive)))
        # フォルダと同じ名前のファイルがあれば、フォルダの名前を変える
        return _unique_path(path) if os.path.isfile(path) else path


class Job:
    """
    圧縮・解凍を別スレッドで実行し、進み具合と結果を持つ。
    func には、Job 自身と args を渡す。
    """

    def __init__(self, func, *args):
        self._func = func
        self._args = args
        self._cancel = threading.Event()
        self._process = None
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self.percentage = 0
        # 利用者に知らせる注意（飛ばした項目など）
        self.warnings = []
        # 失敗したときの例外
        self.error = None

    def start(self):
        self._thread.start()

    def _run(self):
        try:
            self._func(self, *self._args)
        except (ArchiveError, Canceled) as e:
            self.error = e
        except Exception as e:
            log.warning("archive operation failed", exc_info=True)
            self.error = ArchiveError(_error_message(e))

    def wait(self, seconds: float):
        """終わるまで待ち、終わったかどうかを返す"""
        self._thread.join(seconds)
        return self.is_finished()

    def is_finished(self):
        return not self._thread.is_alive()

    def cancel(self):
        """中止を指示する。実際に止まるのは少し後。"""
        self._cancel.set()
        with self._lock:
            if self._process is not None:
                self._process.kill()

    def check_canceled(self):
        if self._cancel.is_set():
            raise Canceled()

    def set_process(self, process):
        """中止のときに終了させるプロセスを登録する"""
        with self._lock:
            self._process = process
            if process is not None and self._cancel.is_set():
                process.kill()

    def set_progress(self, done: int, total: int):
        self.percentage = min(100, done * 100 // total) if total > 0 else 0


# ---- 形式の判定 ----

def get_compress_formats():
    """圧縮に使える形式の一覧を返す"""
    return [
        CompressFormat(".zip", "ZIP", supports_password=True),
        CompressFormat(".7z", "7z", needs_seven_zip=True, supports_password=True),
        CompressFormat(".tar.gz", "TAR.GZ"),
        CompressFormat(".tar.bz2", "TAR.BZ2"),
        CompressFormat(".tar.xz", "TAR.XZ"),
        CompressFormat(".tar", "TAR"),
    ]


def get_extension(path: str):
    """書庫の拡張子（「.tar.gz」などは全体）を小文字で返す。対応していなければ空文字列。"""
    name = os.path.basename(path).lower()
    for extension in (".zip",) + _TAR_EXTENSIONS + tuple(_SINGLE_OPENERS) + _SEVEN_ZIP_EXTENSIONS:
        if name.endswith(extension) and name != extension:
            return extension
    return ""


def get_stem(path: str):
    """書庫の拡張子を除いた名前を返す"""
    name = os.path.basename(path)
    extension = get_extension(path)
    return name[:-len(extension)] if extension else os.path.splitext(name)[0]


def check_extractable(path: str):
    """解凍できる形式か調べ、できなければ理由、できれば空文字列を返す"""
    if get_extension(path) == "":
        return _("%(name)s は、対応していない形式です。") % {"name": os.path.basename(path)}
    return ""


# ---- 圧縮 ----

def compress(job: Job, request: CompressRequest):
    """書庫を作る"""
    if os.path.lexists(request.destination):
        raise ArchiveError(_("同じ名前のファイルまたはフォルダがすでにあります。"))
    entries = _collect_entries(job, request.sources)
    extension = request.archive_format.extension
    temp_directory = tempfile.mkdtemp(prefix=_TEMP_PREFIX, dir=os.path.dirname(request.destination))
    try:
        temp_path = os.path.join(temp_directory, "archive" + extension)
        if request.archive_format.needs_seven_zip or request.password:
            _compress_with_seven_zip(job, request, entries, temp_path)
        elif extension == ".zip":
            _compress_zip(job, entries, temp_path)
        else:
            _compress_tar(job, entries, temp_path, _TAR_MODES[extension])
        job.check_canceled()
        os.rename(temp_path, request.destination)  # 同じ名前のものがあれば失敗する
    finally:
        _remove_tree(temp_directory)


class _Entry:
    """書庫に入れる1項目"""

    def __init__(self, path: str, name: str, is_directory: bool, is_empty: bool, size: int):
        self.path = path
        # 書庫の中での名前（区切りは「/」）
        self.name = name
        self.is_directory = is_directory
        self.is_empty = is_empty
        self.size = size


def _collect_entries(job, sources):
    """圧縮する項目を集める。フォルダへのリンクは、たどると終わらないことがあるので飛ばす。"""
    entries = []
    stack = [(path, os.path.basename(path)) for path in reversed(sources)]
    while stack:
        job.check_canceled()
        path, name = stack.pop()
        if not os.path.isdir(path):
            entries.append(_Entry(path, name, False, False, os.path.getsize(path)))
            continue
        if not _is_real_directory(path):
            job.warnings.append(_("フォルダへのリンクのため圧縮しませんでした: %(path)s") % {"path": path})
            continue
        children = sorted(os.listdir(path))
        entries.append(_Entry(path, name, True, not children, 0))
        stack += [(os.path.join(path, c), name + "/" + c) for c in reversed(children)]
    if not entries:
        raise ArchiveError(_("圧縮できる項目がありません。"))
    return entries


class _Counter:
    """処理した量を進み具合に反映する"""

    def __init__(self, job, total):
        self._job = job
        self._total = total
        self._done = 0

    def add(self, size):
        self._done += size
        self._job.set_progress(self._done, self._total)


class _ProgressReader:
    """読み込んだ量を進み具合に反映し、中止の指示を確認するファイルオブジェクト"""

    def __init__(self, job, file, counter):
        self._job = job
        self._file = file
        self._counter = counter

    def read(self, size=-1):
        self._job.check_canceled()
        data = self._file.read(size)
        self._counter.add(len(data))
        return data


def _compress_zip(job, entries, path):
    counter = _Counter(job, sum(e.size for e in entries))
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, strict_timestamps=False) as archive:
        for entry in entries:
            job.check_canceled()
            if entry.is_directory:
                archive.write(entry.path, entry.name)
                continue
            info = zipfile.ZipInfo.from_file(entry.path, entry.name, strict_timestamps=False)
            info.compress_type = zipfile.ZIP_DEFLATED
            with open(entry.path, "rb") as source, archive.open(info, "w") as out:
                shutil.copyfileobj(_ProgressReader(job, source, counter), out, _CHUNK_SIZE)


def _compress_tar(job, entries, path, mode):
    counter = _Counter(job, sum(e.size for e in entries))
    with tarfile.open(path, mode, dereference=True) as archive:
        for entry in entries:
            job.check_canceled()
            info = archive.gettarinfo(entry.path, entry.name)
            if entry.is_directory:
                archive.addfile(info)
                continue
            with open(entry.path, "rb") as source:
                archive.addfile(info, _ProgressReader(job, source, counter))


def _compress_with_seven_zip(job, request, entries, path):
    # フォルダを渡すと 7-Zip が中のリンクもたどるので、ファイルと空のフォルダだけを渡す
    names = [e.name.replace("/", "\\") for e in entries if not e.is_directory or e.is_empty]
    if not names:
        raise ArchiveError(_("圧縮できる項目がありません。"))
    list_path = os.path.join(os.path.dirname(path), "list.txt")
    with open(list_path, "w", encoding="utf-8") as f:
        f.write("\n".join(names))
    arguments = ["a", "-scsUTF-8", "-spd"]
    if request.password:
        arguments.append("-p" + request.password)
        # 7z は中のファイルの名前も暗号化する。ZIP は、弱い従来の方式ではなく AES を使う
        arguments.append("-mhe=on" if request.archive_format.extension == ".7z" else "-mem=AES256")
    # 「--」より後ろの「@」はファイル名とみなされるので、「--」は使わない
    arguments += [path, "@" + list_path]
    code, message = _run_seven_zip(job, arguments, os.path.dirname(request.sources[0]))
    if code != 0:  # 読み取れないファイルがあったときは 1（警告）になる
        raise ArchiveError(_("圧縮できませんでした。\n%(message)s") % {"message": message})


# ---- 解凍 ----

def extract(job: Job, path: str, directory: str, conflict: str, password: str = ""):
    """書庫を directory に展開する"""
    reason = check_extractable(path)
    if reason:
        raise ArchiveError(reason)
    created = not os.path.isdir(directory)
    os.makedirs(directory, exist_ok=True)
    try:
        staging = tempfile.mkdtemp(prefix=_TEMP_PREFIX, dir=directory)
        try:
            _extract_to_staging(job, path, staging, password)
            job.check_canceled()
            _copy_zone_identifier(path, staging)
            job.check_canceled()
            skipped = _merge(staging, directory, conflict)
            if skipped:
                job.warnings.append(_("同じ名前のファイルがあるため、%(count)d件を展開しませんでした。") % {"count": skipped})
        finally:
            _remove_tree(staging)
    except BaseException:
        if created:
            try:
                os.rmdir(directory)  # 空のときだけ消える
            except OSError:
                pass
        raise


def _extract_to_staging(job, path, staging, password):
    extension = get_extension(path)
    if extension == ".zip":
        _extract_zip(job, path, staging, password)
    elif extension in _TAR_EXTENSIONS:
        _extract_tar(job, path, staging)
    elif extension in _SINGLE_OPENERS:
        _extract_single(job, path, staging, _SINGLE_OPENERS[extension])
    else:
        _extract_with_seven_zip(job, path, staging, password)


def _open_zip(path):
    """
    ZIP を開き、ZipFile と、名前の文字コードのコードページを返す。
    UTF-8 の印がない名前は、UTF-8（macOS など）、Shift_JIS（日本語の Windows）の順に試す。
    """
    for encoding, code_page in (("utf-8", 65001), ("cp932", 932)):
        try:
            return zipfile.ZipFile(path, metadata_encoding=encoding), code_page
        except UnicodeDecodeError:
            pass
    return zipfile.ZipFile(path), 437


def _extract_zip(job, path, staging, password):
    try:
        archive, code_page = _open_zip(path)
    except (zipfile.BadZipFile, NotImplementedError):
        # 分割された ZIP や、一部が壊れた ZIP は 7-Zip なら扱えることがある
        _extract_with_seven_zip(job, path, staging, password)
        return
    with archive:
        infos = archive.infolist()
        if not any(i.flag_bits & 1 or i.compress_type not in _ZIP_METHODS for i in infos):
            _extract_zip_entries(job, archive, infos, staging)
            return
    # 暗号化の復号は Python では遅く、AES などには対応していないので、7-Zip を使う
    _extract_with_seven_zip(job, path, staging, password, ["-mcp=%d" % code_page])


def _extract_zip_entries(job, archive, infos, staging):
    counter = _Counter(job, sum(i.file_size for i in infos))
    for info in infos:
        job.check_canceled()
        if info.is_dir():
            os.makedirs(_get_output_path(staging, info.filename), exist_ok=True)
            continue
        output = _prepare_output(staging, info.filename)
        with archive.open(info) as source:
            _copy_stream(job, source, output, counter.add)
        try:
            _set_time(output, time.mktime(info.date_time + (0, 0, -1)))
        except (ValueError, OverflowError):  # 日時が正しくない
            pass


def _extract_tar(job, path, staging):
    size = os.path.getsize(path)
    with open(path, "rb") as raw, tarfile.open(fileobj=raw, mode="r:*") as archive:
        for info in archive:
            job.check_canceled()
            name = _decode_tar_name(info.name)
            if info.isdir():
                os.makedirs(_get_output_path(staging, name), exist_ok=True)
                continue
            source = None
            if info.isreg() or info.islnk():
                try:
                    source = archive.extractfile(info)
                except KeyError:  # ハードリンクのリンク先が書庫にない
                    pass
            if source is None:  # シンボリックリンクやデバイスファイル
                job.warnings.append(_("展開できない種類の項目を飛ばしました: %(name)s") % {"name": name})
                continue
            output = _prepare_output(staging, name)
            with source:
                _copy_stream(job, source, output, lambda dummy: job.set_progress(raw.tell(), size))
            _set_time(output, info.mtime)


def _extract_single(job, path, staging, opener):
    size = os.path.getsize(path)
    output = _prepare_output(staging, get_stem(path))
    with open(path, "rb") as raw, opener(raw, "rb") as source:
        _copy_stream(job, source, output, lambda dummy: job.set_progress(raw.tell(), size))


def _extract_with_seven_zip(job, path, staging, password, options=()):
    # パスワードがなくても「-p」を付け、入力待ちにならないようにする
    arguments = ["x", "-y", "-spd", "-p" + password, "-o" + staging] + list(options) + ["--", path]
    code, message = _run_seven_zip(job, arguments, None)
    if code > 1:
        if _PASSWORD_ERROR.search(message):
            if password:
                raise PasswordError(_("パスワードが違うか、ファイルが壊れています。"))
            raise PasswordError(_("パスワードが必要です。"))
        raise ArchiveError(_("解凍できませんでした。\n%(message)s") % {"message": message})
    if code == 1 and message:
        job.warnings.append(message)


def _run_seven_zip(job, arguments, cwd):
    """7z.exe を実行し、終了コードとエラーメッセージを返す。引数にパスワードが含まれるので、ログには残さない。"""
    if not os.path.isfile(SEVEN_ZIP_PATH):
        raise ArchiveError(_("圧縮・解凍に必要なファイルが見つかりません。\n%(path)s") % {"path": SEVEN_ZIP_PATH})
    command = [SEVEN_ZIP_PATH, arguments[0], "-bsp1", "-bso0", "-bse2", "-sccUTF-8"] + arguments[1:]
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(
            command, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=errors,
            creationflags=subprocess.CREATE_NO_WINDOW)
        job.set_process(process)
        try:
            # 進み具合は「 12% ファイル名」のように出力される
            while data := process.stdout.read1(4096):
                found = re.findall(rb"(\d{1,3})%", data)
                if found:
                    job.set_progress(int(found[-1]), 100)
            code = process.wait()
        finally:
            job.set_process(None)
            process.stdout.close()
        job.check_canceled()
        errors.seek(0)
        lines = [line.strip() for line in errors.read().decode("utf-8", "replace").splitlines()]
    return code, "\n".join([line for line in lines if line][:_MAX_MESSAGE_LINES])


def _copy_stream(job, source, output, progress):
    """source の内容を新しいファイルに書き込む。progress には、書き込むたびにそのサイズを渡す。"""
    with open(output, "xb") as out:
        while data := source.read(_CHUNK_SIZE):
            job.check_canceled()
            out.write(data)
            progress(len(data))


# ---- 名前とファイルの操作 ----

def _safe_name(name):
    """Windows で使えるファイル名にする"""
    name = _INVALID_CHARS.sub("_", name).rstrip(". ")
    if name == "" or _RESERVED_NAMES.match(name):
        name = "_" + name
    return name


def _get_output_path(staging, name):
    """書庫の中での名前から、展開するパスを作る。展開先の外に出る名前は、中に収まるようにする。"""
    parts = [p for p in re.split(r"[\\/]", name) if p not in ("", ".", "..")]
    return os.path.join(staging, *[_safe_name(p) for p in parts])


def _prepare_output(staging, name):
    """展開するファイルのパスを決め、親のフォルダを作る。同じ名前がすでにあれば番号を付ける。"""
    path = _get_output_path(staging, name)
    if path == staging:  # 名前が「..」だけなど
        path = os.path.join(staging, "_")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return _unique_path(path)


def _decode_tar_name(name):
    """UTF-8 として読めなかった名前を、Shift_JIS として読み直す"""
    try:
        name.encode("utf-8")
        return name
    except UnicodeEncodeError:
        return name.encode("utf-8", "surrogateescape").decode("cp932", "replace")


def _set_time(path, timestamp):
    try:
        os.utime(path, (timestamp, timestamp))
    except (OSError, OverflowError, ValueError):
        pass  # 日時が設定できなくても、展開は続ける


def _unique_path(path):
    """すでにある名前なら「名前 (2).txt」のように番号を付ける"""
    directory, name = os.path.split(path)
    stem, extension = os.path.splitext(name)
    return os.path.join(directory, make_unique_name(directory, stem, extension) + extension)


def make_unique_name(directory: str, stem: str, extension: str):
    """directory にまだない名前（拡張子を除く）を返す"""
    name = stem
    number = 2
    while os.path.lexists(os.path.join(directory, name + extension)):
        name = "%s (%d)" % (stem, number)
        number += 1
    return name


def _is_real_directory(path):
    """リンクではないフォルダか"""
    return os.path.isdir(path) and not os.path.islink(path) and not os.path.isjunction(path)


def _merge(source, destination, conflict):
    """source の中身を destination に移し、飛ばした件数を返す。同じ名前のフォルダはまとめる。"""
    skipped = 0
    for name in os.listdir(source):
        source_path = os.path.join(source, name)
        target = os.path.join(destination, name)
        if not os.path.lexists(target):
            os.rename(source_path, target)
        elif _is_real_directory(source_path) and os.path.isdir(target):
            skipped += _merge(source_path, target, conflict)
        elif conflict == CONFLICT_SKIP:
            skipped += 1
        elif conflict == CONFLICT_OVERWRITE and not os.path.isdir(source_path) and not os.path.isdir(target):
            if os.path.isfile(target):
                os.chmod(target, stat.S_IWRITE)  # 読み取り専用だと置き換えられない
            os.replace(source_path, target)
        else:  # ファイルとフォルダが同じ名前のときは、上書きできないので別の名前にする
            os.rename(source_path, _unique_path(target))
    return skipped


def _copy_zone_identifier(path, directory):
    """インターネットから入手した印が書庫にあれば、展開したファイルにも付ける"""
    try:
        with open(path + ":Zone.Identifier", "rb") as f:
            data = f.read()
    except OSError:
        return
    for root, directories, names in os.walk(directory):
        # 書庫に含まれるリンクをたどって、展開先の外のファイルを変更しないようにする
        directories[:] = [d for d in directories if _is_real_directory(os.path.join(root, d))]
        for name in names:
            file_path = os.path.join(root, name)
            if os.path.islink(file_path):
                continue
            try:
                status = os.stat(file_path)
                with open(file_path + ":Zone.Identifier", "wb") as f:
                    f.write(data)
                os.utime(file_path, ns=(status.st_atime_ns, status.st_mtime_ns))
            except OSError:
                log.warning("could not write zone identifier: %s" % file_path)


def _remove_tree(path):
    """一時フォルダを消す。消せなくても例外にはしない。"""
    def retry(func, target, error):
        try:
            os.chmod(target, stat.S_IWRITE)
            func(target)
        except OSError as e:
            log.warning("could not remove %s: %s" % (target, e))
    shutil.rmtree(path, onexc=retry)


def _error_message(error):
    """例外から、利用者に見せるメッセージを作る"""
    if isinstance(error, (zipfile.BadZipFile, tarfile.TarError, lzma.LZMAError, zlib.error, EOFError, gzip.BadGzipFile)):
        return _("ファイルが壊れているか、書庫ではありません。")
    if isinstance(error, OSError) and error.strerror:
        return "%s\n%s" % (error.strerror, error.filename) if error.filename else error.strerror
    return _("処理に失敗しました。\n%(error)s") % {"error": error}
