import os
import re
from functools import cmp_to_key
import pandas as pd
import datetime

# NON_MERGED_DATASETS_FOLDER = '../out_charge_protocol'
# MERGED_DATASETS_FOLDER = '../merged'
# Round to 3
# NON_MERGED_DATASETS_FOLDER = '../round_raw_data_to_3/out_charge_protocol'
# MERGED_DATASETS_FOLDER = '../round_raw_data_to_3/merged'
# Round to 4
# NON_MERGED_DATASETS_FOLDER = '../round_raw_data_to_4/out_charge_protocol'
# MERGED_DATASETS_FOLDER = '../round_raw_data_to_4/merged'
# Multiply by 1000
NON_MERGED_DATASETS_FOLDER = '../multiply_raw_data_by_1000/out_charge_protocol'
MERGED_DATASETS_FOLDER = '../multiply_raw_data_by_1000/merged'
# Round to 5
NON_MERGED_DATASETS_FOLDER = '../round_raw_data_to_5/out_charge_protocol'
MERGED_DATASETS_FOLDER = '../round_raw_data_to_5/merged'
# Round to 7
NON_MERGED_DATASETS_FOLDER = '../round_raw_data_to_7/out_charge_protocol'
MERGED_DATASETS_FOLDER = '../round_raw_data_to_7/merged'

def compare_filenames(a, b):
    a_date_str = a[23:-4].split('_')
    b_date_str = b[23:-4].split('_')
    a_date = datetime.date(int(a_date_str[2]), int(a_date_str[0]), int(a_date_str[1]))
    b_date = datetime.date(int(b_date_str[2]), int(b_date_str[0]), int(b_date_str[1]))
    if a_date < b_date:
        return -1
    elif a == b:
        return 0
    else:
        return 1

# Merge files in folder to single file in ascending order by date written in filenames
def merge_files():
    non_merged_filenames = sorted(os.listdir(NON_MERGED_DATASETS_FOLDER))  # список папок
    for folder in non_merged_filenames[:]:
        battery_folder_path = os.path.join(NON_MERGED_DATASETS_FOLDER, folder) # folder
        all_battery_files = os.listdir(battery_folder_path) # all files in the folder
        all_battery_files.sort(key=cmp_to_key(compare_filenames))
        df = list()
        last_cycle_index = 0
        for file in all_battery_files[:]: # go through each file
            filepath = os.path.join(battery_folder_path, file)
            csv = pd.read_csv(filepath, sep=',', header=0, index_col=0)
            csv = csv.sort_values(by=['Cycle_Index', 'Step_Index'])
            try:
                csv['Cycle_Index'] = csv.apply(lambda row: int(row['Cycle_Index']) + last_cycle_index, axis=1)
            except:
                print(f'Problem file {file}. Left column size {csv["Cycle_Index"].size}. Right column size {csv.apply(lambda row: int(row["Cycle_Index"]) + last_cycle_index, axis=1).size}')

            last_cycle_index = csv['Cycle_Index'].max()
            df.append(csv)
        df = pd.concat(df)
        actual_name = re.search("[A-Z]{2}2_\d\d", all_battery_files[0]).group()
        df_name = os.path.join(MERGED_DATASETS_FOLDER, actual_name + '_merged.csv')
        df.to_csv(df_name, index=False)


if __name__ == '__main__':
    merge_files()
