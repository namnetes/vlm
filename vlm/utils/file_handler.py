# -*- coding: utf-8 -*-

class FileHandler:
    @staticmethod
    def open_file(filename):
        try:
            return open(filename, 'r', encoding='us-ascii')
        except FileNotFoundError:
            raise FileNotFoundError("The specified file was not found.")
        except PermissionError:
            raise PermissionError("Access denied to the file due to permission issues.")
        except IsADirectoryError:
            raise IsADirectoryError("The specified path is a directory, not a file.")
        except IOError:
            raise IOError("Input/output error occurred while opening the file.")
        except UnicodeDecodeError:
            raise UnicodeDecodeError("Unicode decoding error occurred while reading the file.")

    @staticmethod
    def close_file(file):
        if file:
            file.close()
