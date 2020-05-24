//cl /nologo /EHsc test_contextmenu.cpp user32.lib ole32.lib shell32.lib
#define UNICODE
#include <windows.h>
#include <shlobj.h>
#include <shlwapi.h>
#include <iostream>
#include <sstream>
#include <string>
#include "picojson.h"
#include "defs.h"
using namespace std;

//-------------------------------------------------
//context menu manager

IContextMenu *contextMenu = NULL;
IContextMenu2 *g_pcm2 = NULL;
IContextMenu3 *g_pcm3 = NULL;
HMENU contextMenuHandle = NULL;
HWND hParent = NULL;
WNDPROC parentWindowProc;

wstring rtrimBackSlash(wstring in)
{
	size_t bs = in.rfind(TEXT("\\"));
	if (bs == wstring::npos)
		return TEXT("");
	wstring w2 = in.substr(0, bs);
	return w2;
}

wstring ltrimBackSlash(wstring in)
{
	size_t bs = in.rfind(TEXT("\\"));
	if (bs == wstring::npos)
		return TEXT("");
	wstring w2 = in.substr(bs + 1);
	return w2;
}

LRESULT CALLBACK contextMenuWindowProc(HWND hwnd, UINT uMsg, WPARAM wParam, LPARAM lParam)
{
	if (g_pcm3)
	{
		LRESULT lres;
		if (SUCCEEDED(g_pcm3->HandleMenuMsg2(uMsg, wParam, lParam, &lres)))
		{
			return lres;
		}
	}
	else if (g_pcm2)
	{
		if (SUCCEEDED(g_pcm2->HandleMenuMsg(uMsg, wParam, lParam)))
		{
			return 0;
		}
	}

	return parentWindowProc(hwnd, uMsg, wParam, lParam);
}

int _getContextMenu(LPCTSTR in, HMENU *out)
{
	wstring path = rtrimBackSlash(in);
	wstring file = ltrimBackSlash(in);
	if (path == TEXT(""))
		return 0;

	CoInitialize(NULL);
	IShellFolder *desktop, *fld;
	HRESULT ret = SHGetDesktopFolder(&desktop);
	if (ret != S_OK)
	{
		CoUninitialize();
		return 0;
	}
	DWORD chEaten;
	DWORD dwAttributes;
	LPITEMIDLIST pidl;
	ret = desktop->ParseDisplayName(NULL, NULL, const_cast<wchar_t *>(path.c_str()), &chEaten, &pidl, &dwAttributes);
	if (ret != S_OK)
	{
		desktop->Release();
		CoUninitialize();
		return 0;
	}
	if (desktop->BindToObject(pidl, NULL, IID_IShellFolder, (void **)&fld) != S_OK)
	{
		desktop->Release();
		CoUninitialize();
		return 0;
	}
	ret = fld->ParseDisplayName(NULL, NULL, const_cast<wchar_t *>(file.c_str()), &chEaten, &pidl, &dwAttributes);
	if (ret != S_OK)
	{
		desktop->Release();
		fld->Release();
		CoUninitialize();
		return 0;
	}
	const _ITEMIDLIST *child = ILFindLastID(pidl);
	ret = fld->GetUIObjectOf(NULL, 1, &child, IID_IContextMenu, NULL, (void **)&contextMenu);
	if (ret != S_OK)
	{
		CoTaskMemFree(pidl);
		desktop->Release();
		fld->Release();
		return 0;
	}
	uint uFlags = GetKeyState(VK_SHIFT) < 0 ? CMF_EXTENDEDVERBS : CMF_NORMAL;
	contextMenu->QueryContextMenu(contextMenuHandle, 0, 101, 0x7fff, uFlags);
	contextMenu->QueryInterface(IID_IContextMenu2, (void **)&g_pcm2);
	contextMenu->QueryInterface(IID_IContextMenu3, (void **)&g_pcm3);

	fld->Release();
	desktop->Release();
	CoTaskMemFree(pidl);
	*out = contextMenuHandle;
	return 1;
}

falcon_helper_funcdef int destroyContextMenu()
{
	if (!contextMenu)
		return 0;
	DestroyMenu(contextMenuHandle);
	contextMenu->Release();
	contextMenu = NULL;
	if (g_pcm2)
		g_pcm2->Release();
	if (g_pcm3)
		g_pcm3->Release();
	g_pcm2 = NULL;
	g_pcm3 = NULL;
	CoUninitialize();
	return 1;
}

falcon_helper_funcdef int execContextMenuItem(int nId)
{
	if (!contextMenu)
		return 0;
	CMINVOKECOMMANDINFO info;
	info.cbSize = sizeof(CMINVOKECOMMANDINFO);
	info.fMask = 0;
	info.hwnd = NULL;
	info.lpVerb = (LPCSTR)MAKEINTRESOURCE(nId - 101);
	info.lpParameters = NULL;
	info.lpDirectory = NULL;
	info.nShow = SW_SHOW;
	if (GetKeyState(VK_CONTROL) < 0) {
		info.fMask |= CMIC_MASK_CONTROL_DOWN;
	}
	if (GetKeyState(VK_SHIFT) < 0) {
		info.fMask |= CMIC_MASK_SHIFT_DOWN;
	}
	contextMenu->InvokeCommand(&info);
	return 1;
}

picojson::object *makePicoJsonObject(HMENU menu, int index)
{
	//not used
	MENUITEMINFO menuitem_info;
	memset(&menuitem_info, 0, sizeof(MENUITEMINFO));
	menuitem_info.cbSize = sizeof(MENUITEMINFO);
	menuitem_info.fMask = MIIM_STRING;
	GetMenuItemInfo(menu, index, true, &menuitem_info);
	if (menuitem_info.cch == 0)
	{
		picojson::object *obj = new picojson::object();
		obj->insert(make_pair("type", picojson::value("separator")));
		return obj;
	}
	int sz = (menuitem_info.cch * 2) + 2;
	wchar_t *namebuffer = (wchar_t *)malloc(sz);
	memset(namebuffer, 0, sz);
	MENUITEMINFO menuitem_info2;
	menuitem_info2.cbSize = sizeof(MENUITEMINFO);
	menuitem_info2.fMask = MIIM_SUBMENU | MIIM_STRING | MIIM_FTYPE | MIIM_ID;
	menuitem_info2.dwTypeData = namebuffer;
	menuitem_info2.cch = sz;
	GetMenuItemInfo(menu, index, true, &menuitem_info2);
	int bufsize = WideCharToMultiByte(CP_UTF8, 0, namebuffer, -1, (char *)NULL, 0, NULL, NULL);
	char *utf8 = (char *)malloc(bufsize + 10);
	memset(utf8, 0, bufsize + 10);
	WideCharToMultiByte(CP_UTF8, 0, namebuffer, -1, utf8, bufsize + 10, NULL, NULL);
	picojson::object *obj = new picojson::object();
	obj->insert(make_pair("type", picojson::value("menuitem")));
	obj->insert(make_pair("name", picojson::value(utf8)));
	obj->insert(make_pair("id", picojson::value(static_cast<double>(menuitem_info2.wID))));
	if (menuitem_info2.hSubMenu != NULL)
	{
		picojson::array submenuarray;
		int numItems = GetMenuItemCount(menuitem_info2.hSubMenu);
		for (int i = 0; i < numItems; i++)
		{
			picojson::object *submenuobj = makePicoJsonObject(menuitem_info2.hSubMenu, i);
			submenuarray.push_back(picojson::value(*submenuobj));
			delete (submenuobj);
		}
		obj->insert(make_pair("submenu", picojson::value(submenuarray)));
	}
	free(namebuffer);
	free(utf8);
	return obj;
}

string processMenu(HMENU menu)
{
	int numItems = GetMenuItemCount(menu);
	picojson::object menu_object;
	picojson::array datalist;
	for (int i = 0; i < numItems; ++i)
	{
		picojson::object *obj = makePicoJsonObject(menu, i);
		datalist.push_back(picojson::value(*obj));
		delete (obj);
	}
	menu_object.insert(make_pair("menus", picojson::value(datalist)));
	picojson::value v(menu_object);
	return v.serialize();
}

falcon_helper_funcdef void getContextMenu()
{
	if (contextMenuHandle)
		destroyContextMenu();
	contextMenuHandle = CreatePopupMenu();
}

falcon_helper_funcdef int addContextMenuItemsFromWindows(LPCTSTR path)
{
	HMENU menu;
	return _getContextMenu(path, &menu);
}

falcon_helper_funcdef int showContextMenu(int x, int y)
{
	int cmd = static_cast<int>(TrackPopupMenuEx(contextMenuHandle, TPM_RETURNCMD | TPM_NONOTIFY, x, y, hParent, NULL));
	return cmd;
}

falcon_helper_funcdef void initContextMenu(HWND parent)
{
	hParent = parent;
	parentWindowProc = (WNDPROC)GetWindowLongPtr(parent, GWLP_WNDPROC);
	SetWindowLongPtr(parent, GWLP_WNDPROC, (LONG)contextMenuWindowProc);
}

falcon_helper_funcdef int addCustomContextMenuItem(LPTSTR itemName, int id)
{
	if (!contextMenuHandle)
		return 0;
	MENUITEMINFO mi = {0};
	mi.cbSize = sizeof(MENUITEMINFO);
	mi.fMask = MIIM_STRING;
	mi.fType = MFT_STRING;
	mi.dwTypeData = itemName;
	mi.cch = lstrlen(itemName);
	return InsertMenuItem(contextMenuHandle, id, false, &mi);
}
