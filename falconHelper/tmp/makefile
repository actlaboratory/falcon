OBJS= common.obj ctlcolor.obj findradiobuttons.obj
LIBS= user32.lib Ole32.lib OleAut32.lib gdi32.lib Cfgmgr32.lib Setupapi.lib
.SILENT:
falconHelper.dll: $(OBJS)
	link /nologo /DLL $(OBJS) $(LIBS) /OUT:falconHelper.dll

%.obj: %.cpp
	cl /nologo /EHsc /c /O2 $<

.PHONY: clean
clean:
	rm -rf *.obj
