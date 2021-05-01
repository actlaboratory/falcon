from .base import Output
import clipboardHelper


class Clipboard(Output):
    def speak(self, text, **options):
        with clipboardHelper.Clipboard() as c:
            c.set_unicode_text(text)
