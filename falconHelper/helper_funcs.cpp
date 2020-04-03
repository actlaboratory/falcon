#define UNICODE
#include <windows.h>
#include <string.h>

char *wide2utf8(wchar_t &wide)
{
    int bufsize = WideCharToMultiByte(CP_UTF8, 0, wide, -1, (char *)NULL, 0, NULL, NULL);
    char *utf8 = (char *)malloc(bufsize + 2);
    memset(utf8, 0, bufsize + 2);
    WideCharToMultiByte(CP_UTF8, 0, wide, -1, utf8, bufsize + 2, NULL, NULL);
    return utf8;
}
