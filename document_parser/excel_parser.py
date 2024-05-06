import re
import pandas as pd
from typing import Dict, Union


class ExcelParser:
    def __init__(self, filename: str) -> None:
        self.filename = filename

    def validate_excel_file(self) -> Union[pd.DataFrame, dict]:
        try:
            reader = pd.ExcelFile(self.filename)
        except FileNotFoundError:
            print("File not found")
            reader = {}
        except ValueError:
            print("Given file is not in excel format")
            reader = {}
        return reader

    def parse_excel(self) -> Dict[str, str]:
        excel_reader = self.validate_excel_file()
        if not excel_reader:
            return {}

        res_list = []
        for sheet_name in excel_reader.sheet_names:
            df = excel_reader.parse(sheet_name, usecols=[2,3])
            df.columns = ['group', 'name']
            df.dropna(inplace=True)
            df.reset_index(drop=True, inplace=True)
            df_list = df.values.tolist()
            if len(df_list) <= 1:
                continue
            res_list += df_list

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

def remove_trash_symbols(string: str, is_class: bool) -> str:
    if not string:
        return ""
    string = string.strip() #remove trailing spaces
    string = re.sub(' +', ' ', string) #remove more than one space
    if is_class:
        res = re.search(r'[^a-zA-Z]+', string).start() #get only letters for class
        string = string[0:res]
    return string

