"""
Written By: Nadav Horesh
from IDumper import IDumper
class DumperOneNand(IDumper):
    def dump(self, address, start=0, end=0, step=1, name=""):
        self.open_output(name, "OneNand", address + start, address + end)
        try: