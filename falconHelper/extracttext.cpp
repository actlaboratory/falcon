#define UNICODE
#include <windows.h>
#include <iostream>
#include <string>
#include "defs.h"
#include "helper_funcs.h"
using namespace std;
//Extract text from document files

typedef int (*FUNCTYPE)(BSTR lpFilePath, bool bProp,  BSTR*lpFileText);

wchar_t* extractText(wchar_t *path)
{
    wstring filename=path;
    size_t pos;
    wstring ext;
    bool unsupported;
    pos = filename.rfind(TEXT("."));
    if (pos == wstring::npos)
        return 0;
    ext = filename.substr(pos + 1);
    unsupported = true;
    if (lstrcmpi(ext.c_str(), TEXT("txt")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("pdf")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("rtf")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("docx")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("xlsx")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("pptx")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("doc")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("xls")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("ppt")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("mht")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("html")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("eml")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("sxw")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("sxc")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("sxi")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("sxd")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("odt")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("ods")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("odp")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("odg")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("jaw")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("jtw")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("jbw")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("juw")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("jfw")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("jvw")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("jtd")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("jtt")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("oas")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("oa2")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("oa3")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("bun")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("wj2")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("wj3")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("wk3")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("wk4")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("123")) == 0)
        unsupported = false;
    if (lstrcmpi(ext.c_str(), TEXT("wri")) == 0)
        unsupported = false;
    if (unsupported)
        return NULL;
    wstring content;
    HINSTANCE hInstDLL;
    FUNCTYPE ExtractText;
    if ((hInstDLL = LoadLibrary(TEXT("xd2txlib.dll"))) == NULL)
        return NULL;
    ExtractText = (FUNCTYPE)GetProcAddress(hInstDLL, "ExtractText");
    BSTR fname = SysAllocString(filename.c_str());
    BSTR fileText = SysAllocString(TEXT(""));
    int nFileLength = ExtractText(fname, false, &fileText);
    content = (LPCTSTR)fileText;
    char *ret=wide2utf8(content);
    FreeLibrary(hInstDLL);
    SysFreeString(fname);
    SysFreeString(fileText);
    return ret;
}
