#define UNICODE
#include <windows.h>
#include <iostream>
#include <string>
#include "defs.h"
#include "helper_funcs.h"
using namespace std;
//Extract text from document files

typedef int (*FUNCTYPE)(BSTR lpFilePath, bool bProp,  BSTR*lpFileText);

falcon_helper_funcdef char* extractText(wchar_t *path)
{
    wstring filename=path;
    wstring content;
    HINSTANCE hInstDLL;
    FUNCTYPE ExtractText;
    if ((hInstDLL = LoadLibrary(TEXT("xd2txlib.dll"))) == NULL)
        return NULL;
    ExtractText = (FUNCTYPE)GetProcAddress(hInstDLL, "ExtractText");
    BSTR fname = SysAllocString(filename.c_str());
    BSTR fileText = SysAllocString(TEXT(""));
    int nFileLength = ExtractText(fname, false, &fileText);
    char *ret=wide2utf8(fileText);
    FreeLibrary(hInstDLL);
    SysFreeString(fname);
    SysFreeString(fileText);
    return ret;
}
