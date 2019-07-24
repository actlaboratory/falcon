import clipboard
c=clipboard.ClipboardFile()
c.SetFileList(["C:\git\yncatgithub.pub"])
c.SetOperation(clipboard.MOVE)
c.SendToClipboard()
