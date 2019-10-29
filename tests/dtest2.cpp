// cl /EHsc dtest2.cpp Ole32.lib OleAut32.lib
#define UNICODE
#include <iostream>
#include <string>
#include <windows.h>
#include <imapi2.h>
#include <tchar.h>
int main(int argc, char **argv){
CoInitialize(NULL);
IDiscMaster2* lpDiscMaster=NULL;
HRESULT rMaster=CoCreateInstance(CLSID_MsftDiscMaster2,NULL,CLSCTX_ALL,IID_PPV_ARGS(&lpDiscMaster));
if(rMaster!=S_OK){
std::cout << "not ok";
CoUninitialize();
return 1;
}
std::cout << "OK!" << std::endl;
LONG num=0;
lpDiscMaster->get_Count(&num);
std::cout << "devices: " << num << std::endl;
for(int i=0;i<num;i++){
BSTR tmpUniqueId;
HRESULT r=lpDiscMaster->get_Item(i,&tmpUniqueId);
if(r!=S_OK){
std::cout << "Couldn't get item index " << i << ", skipping..." << std::endl;
continue;
}
IDiscRecorder2* lpRecorder=NULL;
r=CoCreateInstance(CLSID_MsftDiscRecorder2,NULL,CLSCTX_ALL,IID_PPV_ARGS(&lpRecorder));
if(r!=S_OK){
std::cout << "Couldn't create disc recorder, skipping..." << std::endl;
continue;
}
r=lpRecorder->InitializeDiscRecorder(tmpUniqueId);
if(r!=S_OK){
std::cout << "Couldn't initialize disc recorder, skipping..." << std::endl;
continue;
}
SAFEARRAY *drivePaths=NULL;
r=lpRecorder->get_VolumePathNames(&drivePaths);
if(r!=S_OK){
std::cout << "Couldn't get drive paths. Skipping..." << std::endl;
continue;
}
VARIANT* tmp=(VARIANT*)(drivePaths->pvData);
char path[32];
WideCharToMultiByte(CP_ACP,0,(OLECHAR*)(tmp[0].bstrVal),-1,path,sizeof(path)-1,NULL,NULL);
std::cout << path << std::endl;
SafeArrayDestroy(drivePaths);

SAFEARRAY *features=NULL;
r=lpRecorder->get_SupportedFeaturePages(&features);
if(r!=S_OK){
std::cout << "Couldn't get supported features, skipping..." << std::endl;
continue;
}
tmp=(VARIANT*)(features->pvData);
for(int i=0; i<features->rgsabound[0].cElements;i++){
std::cout << "    feature " << tmp[i].lVal << std::endl;
}
SafeArrayDestroy(features);

lpRecorder->Release();
}

lpDiscMaster->Release();
CoUninitialize();
}
