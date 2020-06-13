CPPFLAGS= /nologo /W3 /c /EHsc /O2 /wd4819
OBJS= common.obj contextmenu.obj ctlcolor.obj disctype.obj findradiobuttons.obj ejectDevice.obj extracttext.obj helper_funcs.obj
LIBS= user32.lib Ole32.lib OleAut32.lib gdi32.lib Cfgmgr32.lib Setupapi.lib shell32.lib
.SILENT:
falconHelper.dll: $(OBJS)
	link /nologo /DLL $(OBJS) $(LIBS) /OUT:falconHelper.dll

%.obj: %.cpp
	cl $(CPPFLAGS) $<

.PHONY: clean
clean:
	rm -rf *.obj
