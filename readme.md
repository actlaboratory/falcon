# Falcon
Falcon Python�ōăX�^�[�g�ł���΂����ȁB  
## ����
�V�F��:�R�}���h�v�����v�g  
python:python 3.7  
python -m pip install wxpython  

## ���s  
python falcon.py  

## exe�t�@�C���̃r���h  
64-bit �o�[�W�����̃r���h���@�ł��B32�r�b�g�Ńr���h�������l�͓K���ɁB  
MinGW��C�R���p�C�����_�E�����[�h ( https://sourceforge.net/projects/mingw-w64/ )  
�C���X�g�[����� C:\MinGW64 �Ɠ��͂��ăC���X�g�[��  
�V�X�e�����ϐ��� path �� C:\MinGW64\mingw64\bin ��ǉ�
gcc --version �ł����Ɠ��������m�F  
nuitka(exe�ɂ���c�[��)���C���X�g�[��  
python -m pip install nuitka  
�r���h  
python tools\build.py  
5�����炢���Ԃ�����̂ŋC���ɑ҂���  

## �R�[�f�B���O�K��  
docs �t�H���_�̒��ɏ����Ă���܂��B  

## �|�󎫏��t�@�C��(po)�̃A�b�v�f�[�g
python tools\updateTranslation.py  
locale �t�H���_������ɒT���āApo�t�@�C����z�u���Ă���܂��B�Ȃ̂ŁA�����ǉ��������ꍇ�́Alocale �t�H���_�ɋ�t�H���_������Ă��������B�O��̖|�󕶂͎c�����܂܃}�[�W����܂��B�����񂪑������Ƃ��ł��A�C�ɂ��� updateTranslation ���Ă��������B  

## �|�󂵂���  
python tools\buildTranslation.py  
