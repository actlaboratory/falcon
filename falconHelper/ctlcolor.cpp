#define UNICODE
#include <windows.h>
#include <uxtheme.h>
#include "defs.h"

WNDPROC DefRadioButtonProc, DefCheckboxProc;
HBRUSH bkBrush, whBrush;

LRESULT CALLBACK RadioButtonProc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp)
{
    switch (msg)
    {
    case WM_CTLCOLORSTATIC:
    {
        HDC hDC = (HDC)wp;
        HWND hCtrl = (HWND)lp;
        SetBkMode(hDC, TRANSPARENT);           // �w�i�𓧉�
        SetTextColor(hDC, RGB(255, 255, 255)); // �e�L�X�g�̐F
        SetBkColor(hDC, RGB(0, 0, 0));         // �w�i�̐F
        return (LRESULT)bkBrush;               // �w�i�F�̐F
    }
    }
    return CallWindowProc(DefRadioButtonProc, hwnd, msg, wp, lp);
}

LRESULT CALLBACK CheckboxProc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp)
{
    //MessageBox(NULL,L"a",L"a",MB_OK);
    switch (msg)
    {
    case WM_CTLCOLORSTATIC:
    {
        HDC hDC = (HDC)wp;
        HWND hCtrl = (HWND)lp;
        SetBkMode(hDC, TRANSPARENT);           // �w�i�𓧉�
        SetTextColor(hDC, RGB(255, 255, 255)); // �e�L�X�g�̐F
        SetBkColor(hDC, RGB(0, 0, 0));         // �w�i�̐F
        return (LRESULT)bkBrush;               // �w�i�F�̐F
    }
    }
    return CallWindowProc(DefCheckboxProc, hwnd, msg, wp, lp);
}

falcon_helper_funcdef int ScRadioButton(HWND wnd)
{
    DefRadioButtonProc = (WNDPROC)GetWindowLongPtr(wnd, GWLP_WNDPROC);
    SetWindowLongPtr(wnd, GWLP_WNDPROC, (LONG)RadioButtonProc);
    return 0;
}

falcon_helper_funcdef int ScCheckbox(HWND wnd)
{
    DefCheckboxProc = (WNDPROC)GetWindowLongPtr(wnd, GWLP_WNDPROC);
    SetWindowLongPtr(wnd, GWLP_WNDPROC, (LONG)CheckboxProc);
    return 0;
}

void initCtlcolor()
{
    bkBrush = CreateSolidBrush(RGB(0, 0, 0));
    whBrush = CreateSolidBrush(RGB(255, 255, 255));
}

void freeCtlcolor()
{
    DeleteObject((HGDIOBJ)bkBrush);
    DeleteObject((HGDIOBJ)whBrush);
}
