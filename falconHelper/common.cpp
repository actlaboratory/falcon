#define UNICODE
#include <windows.h>
#include <string.h>
#include "defs.h"
#include "ctlcolor.h"

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
    initCtlcolor();
break;
case DLL_PROCESS_DETACH:
CoUninitialize();
freeCtlcolor();
break;
}
	return TRUE;
}
