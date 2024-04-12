# -*- coding: utf-8 -*-

class FileHandler:
    @staticmethod
    def open_file(filename):
        try:
            return open(filename, 'r', encoding='us-ascii')
        except FileNotFoundError:
            raise FileNotFoundError(f'The specified file, {filename}, was not found.')
        except PermissionError:
            raise PermissionError(f'Access denied to the file, {filename}, due to permission issues.')
        except IsADirectoryError:
            raise IsADirectoryError(f'The specified path, {filename}, is a directory, not a file.')
        except IOError:
            raise IOError(f'Input/output error occurred while opening the file, {filename}.')
        except UnicodeDecodeError:
            raise UnicodeDecodeError(f'Unicode decoding error occurred while reading the file, {filename}.')

    @staticmethod
    def close_file(file):
        if file:
            file.close()
