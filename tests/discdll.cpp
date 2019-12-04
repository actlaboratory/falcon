// cl /nologo /LD /EHsc /O2 discdll.cpp Ole32.lib OleAut32.lib
#define UNICODE
#include <algorithm>
#include <string>
#include <sstream>
#include <vector>
#include <string.h>
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
DVD_PLUS_R_DL_AND_RW,
DVD_R_DL,
DVD_R_DL_AND_RW,
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

std::string _enum2str(int val){
std::string ret="";
switch(val){
case enums::DISC_TYPE::BD_RW:
ret="BD-RW";
break;
case enums::DISC_TYPE::BD_R:
ret="BD-r";
break;
case enums::DISC_TYPE::BD_ROM:
ret="BD-ROM";
break;
case enums::DISC_TYPE::HDDVD_RAM:
ret="HDDVD-RAM";
break;
case enums::DISC_TYPE::HDDVD:
ret="HDDVD";
break;
case enums::DISC_TYPE::HDDVD_ROM:
ret="HDDVD-ROM";
break;
case enums::DISC_TYPE::DVD_PLUS_RW_DL:
ret="DVD+RW DL";
break;
case enums::DISC_TYPE::DVD_PLUS_R_DL:
ret="DVD+R DL";
break;
case enums::DISC_TYPE::DVD_PLUS_R_DL_AND_RW:
ret="DVD+R DL/RW";
break;
case enums::DISC_TYPE::DVD_R_DL:
ret="DVD-R DL";
break;
case enums::DISC_TYPE::DVD_R_DL_AND_RW:
ret="DVD-R DL/RW";
break;
case enums::DISC_TYPE::DVD_RAM:
ret="DVD-RAM";
break;
case enums::DISC_TYPE::DVD_PLUS_RW:
ret="DVD+RW";
break;
case enums::DISC_TYPE::DVD_PLUS_R:
ret="DVD+R";
break;
case enums::DISC_TYPE::DVD_RW:
ret="DVD-RW";
break;
case enums::DISC_TYPE::DVD_R:
ret="DVD-R";
break;
case enums::DISC_TYPE::DVD_ROM:
ret="DVD-ROM";
break;
case enums::DISC_TYPE::CD_RW:
ret="CD-RW";
break;
case enums::DISC_TYPE::CD_R:
ret="CD-R";
break;
case enums::DISC_TYPE::CD_ROM:
ret="CD-ROM";
break;
case enums::DISC_TYPE::MO:
ret="MO";
break;
default:
ret="UNKNOWN";
}
return ret;
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
if(_isIn(val,IMAPI_PROFILE_TYPE_DVD_PLUS_RW_DUAL)){
return enums::DISC_TYPE::DVD_PLUS_RW_DL;
}

if(_isIn(val,IMAPI_PROFILE_TYPE_DVD_PLUS_R_DUAL) && _isIn(val,IMAPI_PROFILE_TYPE_DVD_PLUS_RW)){
return enums::DISC_TYPE::DVD_PLUS_R_DL_AND_RW;
}
if(_isIn(val,IMAPI_PROFILE_TYPE_DVD_PLUS_R_DUAL)){
return enums::DISC_TYPE::DVD_PLUS_R_DL;
}
if(
	(
		_isIn(val,IMAPI_PROFILE_TYPE_DVD_DASH_R_DUAL_SEQUENTIAL) || _isIn(val,IMAPI_PROFILE_TYPE_DVD_DASH_R_DUAL_LAYER_JUMP)
	) && (
		_isIn(val,IMAPI_PROFILE_TYPE_DVD_DASH_REWRITABLE) || _isIn(val,IMAPI_PROFILE_TYPE_DVD_DASH_RW_SEQUENTIAL)
	)
){
return enums::DISC_TYPE::DVD_R_DL_AND_RW;
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

extern "C" __declspec(dllexport) char* getDiscDriveTypes()
{
    IDiscMaster2 *lpDiscMaster = NULL;
    HRESULT rMaster = CoCreateInstance(CLSID_MsftDiscMaster2, NULL, CLSCTX_ALL, IID_PPV_ARGS(&lpDiscMaster));
    if (rMaster != S_OK)
    {
        return NULL;
    }
    LONG num = 0;
    lpDiscMaster->get_Count(&num);
    std::stringstream s;
    for (int i = 0; i < num; i++)
    {
        BSTR tmpUniqueId;
        HRESULT r = lpDiscMaster->get_Item(i, &tmpUniqueId);
        if (r != S_OK)
        {
            continue;
        }
        IDiscRecorder2 *lpRecorder = NULL;
        r = CoCreateInstance(CLSID_MsftDiscRecorder2, NULL, CLSCTX_ALL, IID_PPV_ARGS(&lpRecorder));
        if (r != S_OK)
        {
            continue;
        }
        r = lpRecorder->InitializeDiscRecorder(tmpUniqueId);
        if (r != S_OK)
        {
            //std::cout << "Couldn't initialize disc recorder, skipping..." << std::endl;
            lpRecorder->Release();
            continue;
        }
        SAFEARRAY *drivePaths = NULL;
        r = lpRecorder->get_VolumePathNames(&drivePaths);
        if (r != S_OK)
        {
            //std::cout << "Couldn't get drive paths. Skipping..." << std::endl;
            lpRecorder->Release();
            continue;
        }
        VARIANT *tmp = (VARIANT *)(drivePaths->pvData);
        char path[32];
        WideCharToMultiByte(CP_ACP, 0, (OLECHAR *)(tmp[0].bstrVal), -1, path, sizeof(path) - 1, NULL, NULL);
        //std::cout << path << std::endl;
        SafeArrayDestroy(drivePaths);

        SAFEARRAY *profiles = NULL;
        r = lpRecorder->get_SupportedProfiles(&profiles);
        if (r != S_OK)
        {
            //std::cout << "Couldn't get supported profiles, skipping..." << std::endl;
            lpRecorder->Release();
            continue;
        }
        tmp = (VARIANT *)(profiles->pvData);
        std::vector<int> profile_values;
        for (int i = 0; i < profiles->rgsabound[0].cElements; i++)
        {
            //これコメントアウトしたら、サポートしているプロファイルの一覧が出る
            //std::cout << "    profile " << tmp[i].lVal << std::endl;
            profile_values.push_back(tmp[i].lVal);
        }
        int ejectable= _getEjectability(&profile_values);
        int type= _getDiscType(&profile_values);
        SafeArrayDestroy(profiles);

        s << path << "," << ejectable << "," << _enum2str(type) << std::endl;

        lpRecorder->Release();
    }

    lpDiscMaster->Release();

    std::string ret_s=s.str();
    char* ret=(char*)malloc(ret_s.size()+1);
    memset(ret,0,ret_s.size()+1);
    memcpy(ret,ret_s.c_str(),ret_s.size());
    return ret;
}

extern "C" __declspec(dllexport) void free_ptr(char *p){
free(p);
}

BOOL APIENTRY DllMain(HINSTANCE hInst, DWORD  fdwReason, LPVOID lpReserved) {
switch(fdwReason){
case DLL_PROCESS_ATTACH:
    CoInitialize(NULL);
break;
case DLL_PROCESS_DETACH:
CoUninitialize();
break;
}
	return TRUE;
}
