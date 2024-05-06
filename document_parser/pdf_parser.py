import tabula
from pandas import DataFrame
from typing import Dict, Union, List
from .excel_parser import remove_trash_symbols


class PDFParser:
    def __init__(self, filename: str) -> None:
        self.filename = filename

    def validate_pdf_file(self) -> Union[DataFrame, dict]:
        try:
            reader = tabula.read_pdf(
                self.filename,
                pages='all',
                pandas_options={'header': None},
                guess=False
            )
        except FileNotFoundError:
            print("File not found")
            reader = {}
        except ValueError:
            print("Given file is not in pdf format")
            reader = {}
        except:
            print("Corrupt file, parsing failed")
            reader = {}
        return reader

    def parse_pdf(self) -> Dict[str, str]:
        tables = self.validate_pdf_file()
        if not tables:
            return {}

        res_list = []
        for table in tables:
            df = DataFrame()
            try:
                df = table.iloc[:, [2,3]]
                df = df.dropna()
                df = df.reset_index(drop=True)
            except IndexError:
                continue

            if not is_right_description(df.values.tolist()):
                str_list = table.iloc[:, 0].tolist()
                split_strings = [s.split(' ', 1) for s in str_list if isinstance(s, str)]
                df = DataFrame(split_strings, columns=[0, 1])

            res_list += df.values.tolist()

        my_dict = {}
        if not res_list:
            print("Nothing to read from file")
            return my_dict

        for pair in res_list:
            key = remove_trash_symbols(pair[1], False)
            value = remove_trash_symbols(pair[0], True)
            if not key or not value:
                continue
            my_dict[key] = value
        return my_dict

def is_right_description(array: List[List[str]]) -> bool:
    res = {}
    for pair in array:
        key = remove_trash_symbols(pair[1], False)
        value = remove_trash_symbols(pair[0], True)
        if not key or not value:
            continue
        res[key] = value
    return True if res else False

