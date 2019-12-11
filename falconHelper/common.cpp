// cl /nologo /LD /EHsc /O2 discdll.cpp Ole32.lib OleAut32.lib
#define UNICODE
#include <windows.h>
#include <string.h>
#include "defs.h"

falcon_helper_funcdef void freePtr(char *p){
free(p);
}

falcon_helper_funcdef void copyMemory(void *dest, void *src, size_t sz){
RtlCopyMemory(dest,src,sz);
}

BOOL APIENTRY DllMain(HINSTANCE hInst, DWORD  fdwReason, LPVOID lpReserved) {
switch(fdwReason){
case DLL_PROCESS_ATTACH:
    CoInitialize(NULL);
bkBrush=CreateSolidBrush(RGB(0,0,0));
whBrush=CreateSolidBrush(RGB(255,255,255));
break;
case DLL_PROCESS_DETACH:
CoUninitialize();
DeleteObject((HGDIOBJ)bkBrush);
DeleteObject((HGDIOBJ)whBrush);
break;
}
	return TRUE;
}
