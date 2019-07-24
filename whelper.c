#define UNICODE
#include <windows.h>
#include <uxtheme.h>
WNDPROC DefRadioButtonProc;
HBRUSH bkBrush, whBrush;

LRESULT CALLBACK RadioButtonProc(HWND hwnd , UINT msg , WPARAM wp , LPARAM lp) {
switch(msg){
case WM_CTLCOLORSTATIC:
{
HDC hDC = (HDC)wp;
HWND hCtrl = (HWND)lp;
SetBkMode(hDC, TRANSPARENT);	// îwåiÇìßâﬂ
SetTextColor (hDC, RGB(255,0,0));	// ÉeÉLÉXÉgÇÃêF
SetBkColor (hDC, RGB(0,0,0));	// îwåiÇÃêF
return (LRESULT)bkBrush;	// îwåiêFÇÃêF
}
}
return CallWindowProc(DefRadioButtonProc , hwnd , msg , wp , lp);
}

__declspec(dllexport) int ScRadioButton(HWND wnd){
DefRadioButtonProc = (WNDPROC)GetWindowLongPtr(wnd , GWLP_WNDPROC);
SetWindowLongPtr(wnd , GWLP_WNDPROC , (LONG)RadioButtonProc);
return 0;
}

BOOL APIENTRY DllMain(HINSTANCE hInst, DWORD  fdwReason, LPVOID lpReserved) {
switch(fdwReason){
case DLL_PROCESS_ATTACH:
bkBrush=CreateSolidBrush(RGB(0,0,0));
whBrush=CreateSolidBrush(RGB(255,255,255));
break;
case DLL_PROCESS_DETACH:
DeleteObject((HGDIOBJ)bkBrush);
DeleteObject((HGDIOBJ)whBrush);
break;

}
	return TRUE;
}

__declspec(dllexport) void copyMemory(void *dest, void *src, size_t sz){
RtlCopyMemory(dest,src,sz);
}
