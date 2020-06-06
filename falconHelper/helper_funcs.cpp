#define UNICODE
#include <windows.h>
#include <string.h>

char *wide2utf8(const wchar_t *wide)
{
    int bufsize = WideCharToMultiByte(CP_UTF8, 0, wide, -1, (char *)NULL, 0, NULL, NULL);
    char *utf8 = (char *)malloc(bufsize + 2);
    memset(utf8, 0, bufsize + 2);
    WideCharToMultiByte(CP_UTF8, 0, wide, -1, utf8, bufsize + 2, NULL, NULL);
    return utf8;
}

wchar_t *utf82wide(const char *utf8)
{
    int bufsize = MultiByteToWideChar(CP_UTF8, 0, utf8, -1, (wchar_t *)NULL, 0);
    wchar_t *wide = (wchar_t *)malloc(bufsize + 2);
    memset(wide, 0, bufsize + 2);
    MultiByteToWideChar(CP_UTF8, 0, utf8, -1, wide, bufsize + 2);
    return wide;
}
