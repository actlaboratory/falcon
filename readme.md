# Falcon
Falcon Python�ōăX�^�[�g�ł���΂����ȁB  
## ����
�V�F��:�R�}���h�v�����v�g  
python:python 3.7 (3.8�ɂ���Ɠ����Ȃ��̂ŁA3.7�Œ��)  
python -m pip install -r requirements.txt  

## ���s  
python falcon.py  

## falconHelper�̃r���h  
�l�C�e�B�u�R�[�h�œ������������̂́AC++�ŃM�����M���������Ă����āA falconHelper.dll �ɂȂ��Ă��܂��B������r���h����ɂ́A MSVC �����āA X86 �J���҃R�}���h�E�v�����v�g��ŁA�ȉ��̃R�}���h��ł��Ă��������B  
cd falconHelper  
make  

## exe�t�@�C���̃r���h  
python tools\build.py  

## �R�[�f�B���O�K��  
docs �t�H���_�̒��ɏ����Ă���܂��B  

## �|�󎫏��t�@�C��(po)�̃A�b�v�f�[�g
python tools\updateTranslation.py  
locale �t�H���_������ɒT���āApo�t�@�C����z�u���Ă���܂��B�Ȃ̂ŁA�����ǉ��������ꍇ�́Alocale �t�H���_�ɋ�t�H���_������Ă��������B�O��̖|�󕶂͎c�����܂܃}�[�W����܂��B�����񂪑������Ƃ��ł��A�C�ɂ��� updateTranslation ���Ă��������B  

## �|�󂵂���  
python tools\buildTranslation.py  
