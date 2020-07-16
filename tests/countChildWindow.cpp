#include <windows.h>
#include <iostream>

int count=0;

BOOL CALLBACK EnumChildProc(HWND hwnd , LPARAM lParam){
count++;
std::cout << hwnd << std::endl;
return true;
}

int main(){
HWND parent=(HWND) 0x1c0f38;//change and recompile
EnumChildWindows(parent,EnumChildProc,0);
std::cout << count << "child windows." << std::endl;
return 0;
}

