//cl /nologo /EHsc test_contextmenu.cpp
#define UNICODE
#include <windows.h>
#include <shlobj.h>
#include <shlwapi.h>
#include <iostream>
#include <string>
#include "picojson.h"
using namespace std;

IContextMenu* contextMenu;

HMENU contextMenuHandle;

wstring rtrimBackSlash(wstring in){
size_t bs=in.rfind(TEXT("\\"));
if(bs==wstring::npos) return TEXT("");
wstring w2=in.substr(0,bs);
return w2;
}

wstring ltrimBackSlash(wstring in){
size_t bs=in.rfind(TEXT("\\"));
if(bs==wstring::npos) return TEXT("");
wstring w2=in.substr(bs+1);
return w2;
}

int getContextMenu(LPCTSTR in, HMENU *out){
wstring path=rtrimBackSlash(in);
wstring file=ltrimBackSlash(in);
if(path==TEXT("")) return 0;

CoInitialize(NULL);
IShellFolder *desktop, *fld;
HRESULT ret=SHGetDesktopFolder(&desktop);
if(ret!=S_OK){
CoUninitialize();
 return 0;
}
DWORD chEaten;
DWORD dwAttributes;
LPITEMIDLIST pidl;
ret=desktop->ParseDisplayName(NULL,NULL,const_cast<wchar_t*>(path.c_str()),&chEaten,&pidl,&dwAttributes);
if(ret!=S_OK){
desktop->Release();
CoUninitialize();
 return 0;
}
if(desktop->BindToObject(pidl,NULL,IID_IShellFolder, (void**)&fld)!=S_OK){
desktop->Release();
CoUninitialize();
return 0;
}
ret=fld->ParseDisplayName(NULL,NULL,const_cast<wchar_t*>(file.c_str()),&chEaten,&pidl,&dwAttributes);
if(ret!=S_OK){
desktop->Release();
fld->Release();
CoUninitialize();
return 0;
}
const _ITEMIDLIST* child=ILFindLastID(pidl);
ret=fld->GetUIObjectOf(NULL,1,&child,IID_IContextMenu,NULL,(void**)&contextMenu);
if(ret!=S_OK){
CoTaskMemFree(pidl);
desktop->Release();
fld->Release();
return 0;
}
contextMenuHandle=CreatePopupMenu();
contextMenu->QueryContextMenu(contextMenuHandle,0,101,0x7fff,CMF_NORMAL);
fld->Release();
desktop->Release();
CoTaskMemFree(pidl);
*out=contextMenuHandle;
return 1;
}

int destroyContextMenu(){
if(!contextMenu) return 0;
DestroyMenu(contextMenuHandle);
contextMenu->Release();
CoUninitialize();
return 1;
}

int execContextMenuItem(int nId){
if(!contextMenu) return 0;
CMINVOKECOMMANDINFO info;
info.cbSize=sizeof(CMINVOKECOMMANDINFO);
info.fMask=0;
info.hwnd=NULL;
info.lpVerb=(LPCSTR)MAKEINTRESOURCE(nId-101);
info.lpParameters=NULL;
info.lpDirectory=NULL;
info.nShow=SW_SHOW;
contextMenu->InvokeCommand(&info);
return 1;
}

void processMenu(HMENU menu){
int numItems=GetMenuItemCount(menu);
cout << "Menu has " << numItems << " items." << endl;
picojson::object menu_object;
picojson::array datalist;
bool has_submenu;
UINT cch;
int ret;
for(int i=0;i<numItems;++i){
MENUITEMINFO menuitem_info;
memset(&menuitem_info,0,sizeof(MENUITEMINFO));
menuitem_info.cbSize=sizeof(MENUITEMINFO);
menuitem_info.fMask=MIIM_STRING;
ret=GetMenuItemInfo(menu,i,true,&menuitem_info);
if(menuitem_info.cch==0){
picojson::object obj;
obj.insert(make_pair("type",picojson::value("separator")));
datalist.push_back(picojson::value(obj));
continue;
}
int sz=(menuitem_info.cch*2)+2;
wchar_t *namebuffer=(wchar_t*)malloc(sz);
memset(namebuffer,0,sz);
MENUITEMINFO menuitem_info2;
menuitem_info2.cbSize=sizeof(MENUITEMINFO);
menuitem_info2.fMask=MIIM_SUBMENU|MIIM_STRING|MIIM_FTYPE|MIIM_ID;
menuitem_info2.dwTypeData=namebuffer;
menuitem_info2.cch=sz;
ret=GetMenuItemInfo(menu,i,true,&menuitem_info2);
if(ret==0){
cout << "error" << endl;
free(namebuffer);
continue;
}
int bufsize=WideCharToMultiByte(CP_UTF8,0,namebuffer,-1,(char *)NULL,0,NULL,NULL);
char *utf8=(char*)malloc(bufsize+10);
memset(utf8,0,bufsize+10);
WideCharToMultiByte(CP_UTF8,0,namebuffer,-1,utf8,bufsize+10,NULL,NULL);
has_submenu=menuitem_info2.hSubMenu!=NULL;
picojson::object obj;
obj.insert(make_pair("type",picojson::value("menuitem")));
obj.insert(make_pair("name",picojson::value(utf8)));
obj.insert(make_pair("has_submenu",picojson::value(static_cast<bool>(has_submenu))));
datalist.push_back(picojson::value(obj));
free(namebuffer);
free(utf8);
}
menu_object.insert(make_pair("menus",picojson::value(datalist)));
cout << picojson::value(menu_object) << endl;
}

int main(){
wstring path=L"D:\\log.txt";
HMENU menu;
int ret=getContextMenu(path.c_str(),&menu);
cout << "getContextMenu ret " << ret << endl;
processMenu(menu);
ret=destroyContextMenu();
cout << "destroyContextMenu ret " << ret << endl;
return 0;
}
