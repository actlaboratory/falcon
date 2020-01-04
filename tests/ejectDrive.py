import win32file
import re

deviceName=win32file.QueryDosDevice("E:")
deviceName=re.sub(r"\\Device\\([^\x00]+).*",r"\1",deviceName)

handle=win32file.CreateFile(
	"\\\\.\\"+deviceName,
	win32file.GENERIC_WRITE | win32file.GENERIC_READ,
	0,	#�N���[�Y����܂ő������OPEN�ł��Ȃ�
	None, #�Z�L�����e�B�֘A�̍\����
	win32file.OPEN_EXISTING,	#�f�o�C�X��OPEN�͂��ꂶ��Ȃ��ƃ_��
	0, 
	None)
print(handle)

print(win32file.DeviceIoControl(handle,0x2D4808,None,None))	#IOCTL_STORAGE_EJECT_MEDIA

print(handle.Close())
