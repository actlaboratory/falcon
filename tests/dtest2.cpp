// cl /EHsc dtest2.cpp Ole32.lib OleAut32.lib
#define UNICODE
#include <algorithm>
#include <iostream>
#include <string>
#include <vector>
#include <windows.h>
#include <imapi2.h>
#include <tchar.h>
namespace enums{
enum DISC_TYPE{
BD_RW=0,
BD_R,
BD_ROM,
HDDVD_RAM,
HDDVD,
HDDVD_ROM,
DVD_PLUS_RW_DL,
DVD_PLUS_R_DL,
DVD_R_DL,
DVD_RAM,
DVD_PLUS_RW,
DVD_PLUS_R,
DVD_RW,
DVD_R,
DVD_ROM,
CD_RW,
CD_R,
CD_ROM,
MO
};
}

int _isIn(std::vector<int> *v, int val){
auto result = std::find((*v).begin(), (*v).end(), val);
return result != (*v).end();
}

int _getEjectability(std::vector<int> *val){
return _isIn(val,IMAPI_PROFILE_TYPE_REMOVABLE_DISK);
}

int _getDiscType(std::vector<int> *val){
if(_isIn(val,IMAPI_PROFILE_TYPE_BD_REWRITABLE)){
return enums::DISC_TYPE::BD_RW;
}
if(_isIn(val,IMAPI_PROFILE_TYPE_BD_R_RANDOM_RECORDING) || _isIn(val,IMAPI_PROFILE_TYPE_BD_R_SEQUENTIAL)){
return enums::DISC_TYPE::BD_R;
}
if(_isIn(val,IMAPI_PROFILE_TYPE_BD_ROM)){
return enums::DISC_TYPE::BD_ROM;
}
if(_isIn(val,IMAPI_PROFILE_TYPE_HD_DVD_RAM)){
return enums::DISC_TYPE::HDDVD_RAM;
}
if(_isIn(val,IMAPI_PROFILE_TYPE_HD_DVD_RECORDABLE)){
return enums::DISC_TYPE::HDDVD;
}
if(_isIn(val,IMAPI_PROFILE_TYPE_HD_DVD_ROM)){
return enums::DISC_TYPE::HDDVD_ROM;
}
if(_isIn(val,IMAPI_PROFILE_TYPE_HD_DVD_ROM)){
return enums::DISC_TYPE::HDDVD_ROM;
}
if(_isIn(val,IMAPI_PROFILE_TYPE_DVD_PLUS_RW_DUAL)){
return enums::DISC_TYPE::DVD_PLUS_RW_DL;
}
if(_isIn(val,IMAPI_PROFILE_TYPE_DVD_PLUS_R_DUAL)){
return enums::DISC_TYPE::DVD_PLUS_R_DL;
}
if(_isIn(val,IMAPI_PROFILE_TYPE_DVD_DASH_R_DUAL_SEQUENTIAL) || _isIn(val,IMAPI_PROFILE_TYPE_DVD_DASH_R_DUAL_LAYER_JUMP)){
return enums::DISC_TYPE::DVD_R_DL;
}
if(_isIn(val,IMAPI_PROFILE_TYPE_DVD_RAM)){
return enums::DISC_TYPE::DVD_RAM;
}
if(_isIn(val,IMAPI_PROFILE_TYPE_DVD_PLUS_RW)){
return enums::DISC_TYPE::DVD_PLUS_RW;
}
if(_isIn(val,IMAPI_PROFILE_TYPE_DVD_PLUS_R)){
return enums::DISC_TYPE::DVD_PLUS_R;
}
if(_isIn(val,IMAPI_PROFILE_TYPE_DVD_DASH_REWRITABLE) || _isIn(val,IMAPI_PROFILE_TYPE_DVD_DASH_RW_SEQUENTIAL)){
return enums::DISC_TYPE::DVD_RW;
}
if(_isIn(val,IMAPI_PROFILE_TYPE_DVD_DASH_RECORDABLE)){
return enums::DISC_TYPE::DVD_R;
}
if(_isIn(val,IMAPI_PROFILE_TYPE_DVDROM)){
return enums::DISC_TYPE::DVD_ROM;
}
if(_isIn(val,IMAPI_PROFILE_TYPE_CD_REWRITABLE)){
return enums::DISC_TYPE::CD_RW;
}
if(_isIn(val,IMAPI_PROFILE_TYPE_CD_RECORDABLE)){
return enums::DISC_TYPE::CD_R;
}
if(_isIn(val,IMAPI_PROFILE_TYPE_CDROM)){
return enums::DISC_TYPE::CD_ROM;
}
if(_isIn(val,IMAPI_PROFILE_TYPE_MO_ERASABLE) || _isIn(val,IMAPI_PROFILE_TYPE_AS_MO) || _isIn(val,IMAPI_PROFILE_TYPE_AS_MO)){
return enums::DISC_TYPE::MO;
}
return -1;
}

int main(int argc, char **argv)
{
    CoInitialize(NULL);
    IDiscMaster2 *lpDiscMaster = NULL;
    HRESULT rMaster = CoCreateInstance(CLSID_MsftDiscMaster2, NULL, CLSCTX_ALL, IID_PPV_ARGS(&lpDiscMaster));
    if (rMaster != S_OK)
    {
        std::cout << "not ok";
        CoUninitialize();
        return 1;
    }
    LONG num = 0;
    lpDiscMaster->get_Count(&num);
    std::cout << "devices: " << num << std::endl;
    for (int i = 0; i < num; i++)
    {
        BSTR tmpUniqueId;
        HRESULT r = lpDiscMaster->get_Item(i, &tmpUniqueId);
        if (r != S_OK)
        {
            std::cout << "Couldn't get item index " << i << ", skipping..." << std::endl;
            continue;
        }
        IDiscRecorder2 *lpRecorder = NULL;
        r = CoCreateInstance(CLSID_MsftDiscRecorder2, NULL, CLSCTX_ALL, IID_PPV_ARGS(&lpRecorder));
        if (r != S_OK)
        {
            std::cout << "Couldn't create disc recorder, skipping..." << std::endl;
            continue;
        }
        r = lpRecorder->InitializeDiscRecorder(tmpUniqueId);
        if (r != S_OK)
        {
            std::cout << "Couldn't initialize disc recorder, skipping..." << std::endl;
            continue;
        }
        SAFEARRAY *drivePaths = NULL;
        r = lpRecorder->get_VolumePathNames(&drivePaths);
        if (r != S_OK)
        {
            std::cout << "Couldn't get drive paths. Skipping..." << std::endl;
            continue;
        }
        VARIANT *tmp = (VARIANT *)(drivePaths->pvData);
        char path[32];
        WideCharToMultiByte(CP_ACP, 0, (OLECHAR *)(tmp[0].bstrVal), -1, path, sizeof(path) - 1, NULL, NULL);
        std::cout << path << std::endl;
        SafeArrayDestroy(drivePaths);

        SAFEARRAY *features = NULL;
        r = lpRecorder->get_SupportedFeaturePages(&features);
        if (r != S_OK)
        {
            std::cout << "Couldn't get supported features, skipping..." << std::endl;
            continue;
        }
        tmp = (VARIANT *)(features->pvData);
        for (int i = 0; i < features->rgsabound[0].cElements; i++)
        {
            //����R�����g�A�E�g������A�Ή����Ă���@�\�̔ԍ����o��
            //std::cout << "    feature " << tmp[i].lVal << std::endl;
        }
        SafeArrayDestroy(features);

        SAFEARRAY *profiles = NULL;
        r = lpRecorder->get_SupportedProfiles(&profiles);
        if (r != S_OK)
        {
            std::cout << "Couldn't get supported profiles, skipping..." << std::endl;
            continue;
        }
        tmp = (VARIANT *)(profiles->pvData);
        std::vector<int> profile_values;
        for (int i = 0; i < profiles->rgsabound[0].cElements; i++)
        {
            //����R�����g�A�E�g������A�T�|�[�g���Ă���v���t�@�C���̈ꗗ���o��
            //std::cout << "    profile " << tmp[i].lVal << std::endl;
            profile_values.push_back(tmp[i].lVal);
        }
        std::cout << "Ejectable: " << _getEjectability(&profile_values) << std::endl;
        std::cout << "Drive type: " << _getDiscType(&profile_values) << std::endl;
        SafeArrayDestroy(profiles);

        lpRecorder->Release();
    }

    lpDiscMaster->Release();
    CoUninitialize();
}
