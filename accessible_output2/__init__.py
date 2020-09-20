from __future__ import absolute_import
import ctypes
import os
import sys
import types
from platform_utils import paths

#Python3.8以降での実行時のみ、dllの探索対象ディレクトリの指定が必要
if sys.version_info.major>=3 and sys.version_info.minor>=8:
	if paths.is_frozen():
		os.add_dll_directory(os.path.join(paths.embedded_data_path(), 'accessible_output2', 'lib'))
	else:
		os.add_dll_directory(os.path.join(paths.module_path(), 'lib'))

def load_library(libname, cdll=False):
	if paths.is_frozen():
		libfile = os.path.join(paths.embedded_data_path(), 'accessible_output2', 'lib', libname)
	else:
		libfile = os.path.join(paths.module_path(), 'lib', libname)
	if cdll:
		return ctypes.cdll[libfile]
	else:
		return ctypes.windll[libfile]

def get_output_classes():
	from . import outputs
	module_type = types.ModuleType
	classes = [m.output_class for m in outputs.__dict__.values() if type(m) == module_type and hasattr(m, 'output_class')]
	return sorted(classes, key=lambda c: c.priority)

def find_datafiles():
	import os
	import platform
	from glob import glob
	import accessible_output2
	if platform.system() != 'Windows':
		return []
	path = os.path.join(accessible_output2.__path__[0], 'lib', '*.dll')
	results = glob(path)
	dest_dir = os.path.join('accessible_output2', 'lib')
	return [(dest_dir, results)]
