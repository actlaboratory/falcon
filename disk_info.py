# -*- coding: utf-8 -*-
# Falcon disk information
# Note: All comments except these top lines will be written in Japanese.

"""
ドライブの詳細情報を調べる。

- ディスク（ローカル ディスク・リムーバブル ディスク・光学ドライブ）の型番・接続方式・SSD/HDD の別・容量
- 光学ドライブに入っているメディアの種類（CD-R・DVD+RW など）と状態

ドライブに問い合わせるため、時間がかかることがある（光学ドライブは、しばらく使っていないと10秒以上）。
メインスレッドからは呼ばず、background_wait.run() などで別スレッドから使う。
いずれも管理者権限は不要。
"""

import logging
import struct

import pythoncom
import pywintypes
import win32com.client
import win32file

log = logging.getLogger("falcon.disk_info")

_IOCTL_STORAGE_QUERY_PROPERTY = 0x2D1400
_IOCTL_VOLUME_GET_VOLUME_DISK_EXTENTS = 0x560000
_IOCTL_DISK_GET_DRIVE_GEOMETRY_EX = 0x700A0

# STORAGE_PROPERTY_ID
_STORAGE_DEVICE_PROPERTY = 0
_STORAGE_DEVICE_SEEK_PENALTY_PROPERTY = 7

# STORAGE_BUS_TYPE と表示名
_BUS_TYPE_NAMES = {
    0x01: "SCSI",
    0x02: "ATAPI",
    0x03: "ATA",
    0x04: "IEEE 1394",
    0x05: "SSA",
    0x06: _("ファイバー チャネル"),
    0x07: "USB",
    0x08: "RAID",
    0x09: "iSCSI",
    0x0A: "SAS",
    0x0B: "SATA",
    0x0C: "SD",
    0x0D: "MMC",
    0x0E: _("仮想"),
    0x0F: _("仮想（ファイル）"),
    0x10: _("記憶域スペース"),
    0x11: "NVMe",
    0x12: "SCM",
    0x13: "UFS",
}

# 光学メディアのプロファイル番号（IMAPI_PROFILE_TYPE）と表示名
_DISC_PROFILE_NAMES = {
    0x08: "CD-ROM",
    0x09: "CD-R",
    0x0A: "CD-RW",
    0x10: "DVD-ROM",
    0x11: "DVD-R",
    0x12: "DVD-RAM",
    0x13: "DVD-RW",
    0x14: "DVD-RW",
    0x15: "DVD-R DL",
    0x16: "DVD-R DL",
    0x1A: "DVD+RW",
    0x1B: "DVD+R",
    0x2A: "DVD+RW DL",
    0x2B: "DVD+R DL",
    0x40: "BD-ROM",
    0x41: "BD-R",
    0x42: "BD-R",
    0x43: "BD-RE",
    0x50: "HD DVD-ROM",
    0x51: "HD DVD-R",
    0x52: "HD DVD-RAM",
}

# IMAPI_FORMAT2_DATA_MEDIA_STATE と表示名（表示する順）
_MEDIA_STATE_NAMES = (
    (0x0002, _("空")),
    (0x0004, _("追記可能")),
    (0x0001, _("上書き可能")),
    (0x4000, _("ファイナライズ済み")),
    (0x2000, _("書き込み禁止")),
    (0x0800, _("消去が必要")),
    (0x0400, _("破損")),
)
_MEDIA_STATE_BLANK = 0x0002
_MEDIA_STATE_FINALIZED = 0x4000
_MEDIA_STATE_FINAL_SESSION = 0x0008

_SECTOR_SIZE = 2048


class DiskInfo:
    """ドライブがあるディスク（物理ディスク）の情報。調べられなかった項目は空文字列や None になる。"""

    def __init__(self):
        # 物理ディスクの番号（タスクマネージャーの「ディスク 0」の番号）。複数のディスクにまたがることがある
        self.disk_numbers = []
        self.model = ""
        self.bus_type = ""
        # SSD なら True、HDD なら False、分からなければ None
        self.is_ssd = None
        # 物理ディスクの容量（バイト）。分からなければ -1
        self.size = -1


class DiscMediaInfo:
    """光学ドライブに入っているメディアの情報"""

    def __init__(self):
        # メディアの種類（"CD-R" など）。入っていなければ空文字列
        self.media_type = ""
        # 状態の表示名のリスト（"空" など）。書き込めないメディアなどでは空
        self.states = []
        # 何も書き込まれていなければ True
        self.is_blank = False
        # 書き込める容量（バイト）。分からなければ -1
        self.free_for_writing = -1


def _open_device(path):
    """デバイスを、読み書きの権限なしで開く（情報の問い合わせだけなら管理者権限は要らない）"""
    return win32file.CreateFile(
        path,
        0,
        win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
        None,
        win32file.OPEN_EXISTING,
        0,
        None)


def _query_property(handle, property_id, size=1024):
    """IOCTL_STORAGE_QUERY_PROPERTY で、指定した情報を問い合わせる"""
    # STORAGE_PROPERTY_QUERY: PropertyId, QueryType(PropertyStandardQuery), AdditionalParameters
    query = struct.pack("<II4x", property_id, 0)
    return bytes(win32file.DeviceIoControl(handle, _IOCTL_STORAGE_QUERY_PROPERTY, query, size))


def _read_string(buffer, offset):
    """STORAGE_DEVICE_DESCRIPTOR 内の、指定位置から始まる文字列を取り出す"""
    if offset == 0 or offset >= len(buffer):
        return ""
    end = buffer.find(b"\0", offset)
    if end < 0:
        end = len(buffer)
    return buffer[offset:end].decode("ascii", "replace").strip()


def _get_disk_numbers(volume_handle):
    """ボリュームがある物理ディスクの番号のリストを返す。調べられなければ空のリストを返す"""
    try:
        buffer = bytes(win32file.DeviceIoControl(volume_handle, _IOCTL_VOLUME_GET_VOLUME_DISK_EXTENTS, None, 1024))
    except pywintypes.error:
        return []  # 光学ドライブなど
    count = struct.unpack_from("<I", buffer)[0]
    numbers = []
    for i in range(count):
        # DISK_EXTENT: DiskNumber, (パディング), StartingOffset, ExtentLength
        number = struct.unpack_from("<I", buffer, 8 + i * 24)[0]
        if number not in numbers:
            numbers.append(number)
    return numbers


def _load_device_info(handle, info):
    """型番・接続方式・SSD/HDD の別・容量を調べて info に入れる"""
    try:
        buffer = _query_property(handle, _STORAGE_DEVICE_PROPERTY)
        # STORAGE_DEVICE_DESCRIPTOR: Version, Size, DeviceType, DeviceTypeModifier, RemovableMedia, CommandQueueing,
        # VendorIdOffset, ProductIdOffset, ProductRevisionOffset, SerialNumberOffset, BusType
        values = struct.unpack_from("<IIBBBBIIIII", buffer)
        vendor = _read_string(buffer, values[6])
        product = _read_string(buffer, values[7])
        # 型番に製造元の名前が含まれていることが多い
        if vendor and not product.lower().startswith(vendor.lower()):
            info.model = "%s %s" % (vendor, product)
        else:
            info.model = product
        info.model = " ".join(info.model.split())
        info.bus_type = _BUS_TYPE_NAMES.get(values[10], "")
    except pywintypes.error as e:
        log.debug("cannot get the device property: %s" % e)
    try:
        # DEVICE_SEEK_PENALTY_DESCRIPTOR: Version, Size, IncursSeekPenalty
        buffer = _query_property(handle, _STORAGE_DEVICE_SEEK_PENALTY_PROPERTY, 12)
        info.is_ssd = not struct.unpack_from("<IIB", buffer)[2]
    except pywintypes.error as e:
        log.debug("cannot get the seek penalty: %s" % e)
    try:
        # DISK_GEOMETRY_EX: DISK_GEOMETRY(24バイト), DiskSize, ...
        buffer = bytes(win32file.DeviceIoControl(handle, _IOCTL_DISK_GET_DRIVE_GEOMETRY_EX, None, 256))
        info.size = struct.unpack_from("<q", buffer, 24)[0]
    except pywintypes.error as e:
        log.debug("cannot get the disk size: %s" % e)


def get_disk_info(letter):
    """
    (別スレッド)ドライブがあるディスクの情報を調べて DiskInfo を返す。
    ネットワークドライブなど、調べられないときは None を返す。
    """
    try:
        volume = _open_device("\\\\.\\%s:" % letter)
    except pywintypes.error as e:
        log.debug("cannot open the volume %s: %s" % (letter, e))
        return None
    info = DiskInfo()
    try:
        info.disk_numbers = _get_disk_numbers(volume)
        if not info.disk_numbers:
            _load_device_info(volume, info)
            return info
    finally:
        volume.Close()
    # 複数のディスクにまたがる場合は、最初のディスクの情報を表示する
    try:
        disk = _open_device("\\\\.\\PhysicalDrive%d" % info.disk_numbers[0])
    except pywintypes.error as e:
        log.debug("cannot open the disk %d: %s" % (info.disk_numbers[0], e))
        return info
    try:
        _load_device_info(disk, info)
    finally:
        disk.Close()
    return info


def _find_disc_recorder(letter):
    """指定したドライブレターの光学ドライブの IDiscRecorder2 を返す。見つからなければ None を返す"""
    path = "%s:\\" % letter.upper()
    master = win32com.client.Dispatch("IMAPI2.MsftDiscMaster2")
    for unique_id in master:
        recorder = win32com.client.Dispatch("IMAPI2.MsftDiscRecorder2")
        recorder.InitializeDiscRecorder(unique_id)
        if path in [p.upper() for p in recorder.VolumePathNames]:
            return recorder
    return None


def get_disc_media_info(letter):
    """
    (別スレッド)光学ドライブに入っているメディアの情報を調べて DiscMediaInfo を返す。COM を初期化してから呼ぶこと。
    光学ドライブが見つからないなど、調べられないときは None を返す。
    """
    try:
        recorder = _find_disc_recorder(letter)
    except pythoncom.com_error as e:
        log.warning("cannot get the disc recorder of %s: %s" % (letter, e))
        return None
    if recorder is None:
        return None
    info = DiscMediaInfo()
    for profile in recorder.CurrentProfiles:
        if profile in _DISC_PROFILE_NAMES:
            info.media_type = _DISC_PROFILE_NAMES[profile]
            break
    if info.media_type == "":
        return info  # メディアが入っていない
    try:
        data_format = win32com.client.Dispatch("IMAPI2.MsftDiscFormat2Data")
        if not data_format.IsCurrentMediaSupported(recorder):
            return info  # 書き込めないメディア
        data_format.Recorder = recorder
        status = data_format.CurrentMediaStatus
        info.states = [name for flag, name in _MEDIA_STATE_NAMES if status & flag]
        info.is_blank = bool(status & _MEDIA_STATE_BLANK)
        if not status & (_MEDIA_STATE_FINALIZED | _MEDIA_STATE_FINAL_SESSION):
            info.free_for_writing = data_format.FreeSectorsOnMedia * _SECTOR_SIZE
    except pythoncom.com_error as e:
        log.debug("cannot get the media status of %s: %s" % (letter, e))
    return info


def load_drive_details(task, letter, is_disc):
    """
    (別スレッド)background_wait.run() で使う。ディスクの情報と、光学ドライブならメディアの情報を調べる。
    (DiskInfo または None, DiscMediaInfo または None) を返す。
    """
    disk = get_disk_info(letter)
    task.check_canceled()
    media = get_disc_media_info(letter) if is_disc else None
    return disk, media
