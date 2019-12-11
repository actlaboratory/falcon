OBJS= common.obj ctlcolor.obj disctype.obj findradiobuttons.obj
LIBS= user32.lib Ole32.lib OleAut32.lib
falconHelper.dll: $(OBJS)
	cl /nologo /LD /EHsc /O2 /Fe falconHelper.dll $(OBJS) $(LIBS)

.cpp.o:
	cl /nologo /O2 $<
