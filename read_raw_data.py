import os
from os import listdir
from os.path import isfile, join
import scipy.io
import pandas as pd
import numpy as np
import re

def convert_to_milli_and_round_to_3_signs(x):
    return round(x*1000, 3)

def process_data(battery_data):
    # Only charge protocol should be left (Current > 0)
    charge_protocol = battery_data[battery_data['Current(A)'] > 0]

    # Round data
    charge_protocol['Current(A)'] = charge_protocol['Current(A)'].apply(lambda x: round(x, 7)) # lambda - анонимная функция
    charge_protocol['Voltage(V)'] = charge_protocol['Voltage(V)'].apply(lambda x: round(x, 7))

    # Multiply data by 1000
    # charge_protocol['Current(A)'] = charge_protocol['Current(A)'].apply(convert_to_milli_and_round_to_3_signs) # именованная функция
    # charge_protocol['Voltage(V)'] = charge_protocol['Voltage(V)'].apply(convert_to_milli_and_round_to_3_signs)

    # Take only charge protocol (CC and CV steps)
    cc_charge_protocol = charge_protocol[charge_protocol['Step_Index'] == 2]  # CC step
    cv_charge_protocol = charge_protocol[charge_protocol['Step_Index'] == 4]  # CV step
    # CC step: extract data corresponding to voltage limits
    cc_charge_protocol_voltage_limits = cc_charge_protocol[
        (cc_charge_protocol['Voltage(V)'] < voltage_high_limit) & (
                cc_charge_protocol['Voltage(V)'] > voltage_low_limit)]
    # apply normalization by column 'Voltage(V)'
    cc_charge_protocol_voltage_limits_normalized = (cc_charge_protocol_voltage_limits['Voltage(V)'] -
                                                    cc_charge_protocol_voltage_limits['Voltage(V)'].min()) / (
                                                           cc_charge_protocol_voltage_limits[
                                                               'Voltage(V)'].max() -
                                                           cc_charge_protocol_voltage_limits[
                                                               'Voltage(V)'].min())
    # Add this column to the existing dataframe 'cc_charge_protocol_voltage_limits'
    cc_charge_protocol_voltage_limits['Voltage_Norm_CC'] = cc_charge_protocol_voltage_limits_normalized
    # apply normalization by column 'Test_Time(s)'
    cc_charge_protocol_time_normalized = (cc_charge_protocol_voltage_limits[
                                              'Test_Time(s)'] -
                                          cc_charge_protocol_voltage_limits[
                                              'Test_Time(s)'].min()) / (
                                                 cc_charge_protocol_voltage_limits[
                                                     'Test_Time(s)'].max() -
                                                 cc_charge_protocol_voltage_limits[
                                                     'Test_Time(s)'].min())
    # Add this column to the existing dataframe 'cc_charge_protocol_voltage_limits'
    cc_charge_protocol_voltage_limits['Test_Time_Norm_CC'] = cc_charge_protocol_time_normalized
    # CV step: extract data corresponding to current limits
    cv_charge_protocol_current_limits = cv_charge_protocol[
        (cv_charge_protocol['Current(A)'] < current_high_limit) & (
                cv_charge_protocol['Current(A)'] > current_low_limit)]
    # apply normalization by column 'Current(A)'
    cv_charge_protocol_current_limits_normalized = (cv_charge_protocol_current_limits[
                                                        'Current(A)'] -
                                                    cv_charge_protocol_current_limits[
                                                        'Current(A)'].min()) / (
                                                           cv_charge_protocol_current_limits[
                                                               'Current(A)'].max() -
                                                           cv_charge_protocol_current_limits[
                                                               'Current(A)'].min())
    # add this column to the existing dataframe 'cv_charge_protocol_current_limits'
    cv_charge_protocol_current_limits['Current_Norm_CV'] = cv_charge_protocol_current_limits_normalized
    # time during CV normalized
    cv_charge_protocol_time_normalized = (cv_charge_protocol_current_limits[
                                              'Test_Time(s)'] -
                                          cv_charge_protocol_current_limits[
                                              'Test_Time(s)'].min()) / (
                                                 cv_charge_protocol_current_limits[
                                                     'Test_Time(s)'].max() -
                                                 cv_charge_protocol_current_limits[
                                                     'Test_Time(s)'].min())
    # Add this column to the existing dataframe 'cv_charge_protocol_current_limits'
    cv_charge_protocol_current_limits['Test_Time_Norm_CV'] = cv_charge_protocol_time_normalized
    # unite CC and CV steps to one dataset
    charge_steps = [cc_charge_protocol_voltage_limits, cv_charge_protocol_current_limits]
    cc_cv_charge_protocol = pd.concat(charge_steps)
    # save united dataset
    cc_cv_charge_protocol_name = os.path.join(GROUP_1_OUT_CHARGE_PROTOCOL_FOLDER_PATH, folder,
                                              'charge_protocol_' + curr_file_name + '.csv')
    cc_cv_charge_protocol.to_csv(cc_cv_charge_protocol_name)


# Extract charge protocol and specific segments of current and voltage for each battery
if __name__ == "__main__":
    # Reading raw data of Group 1 batteries CS2_ (CALCE dataset)
    GROUP_1_RAW_DATA_FOLDER_PATH = '../group_one_raw_data'
    # GROUP_1_OUT_CHARGE_PROTOCOL_FOLDER_PATH = '../out_group_one_charge_protocol'
    # Round to 3
    # GROUP_1_OUT_CHARGE_PROTOCOL_FOLDER_PATH = '../round_raw_data_to_3/out_charge_protocol'
    #Round to 4
    # GROUP_1_OUT_CHARGE_PROTOCOL_FOLDER_PATH = '../round_raw_data_to_4/out_charge_protocol'
    #Multiply by 1000
    # GROUP_1_OUT_CHARGE_PROTOCOL_FOLDER_PATH = '../multiply_raw_data_by_1000/out_charge_protocol'
    #Round to 5
    # GROUP_1_OUT_CHARGE_PROTOCOL_FOLDER_PATH = '../round_raw_data_to_5/out_charge_protocol'
    #Round to 7
    GROUP_1_OUT_CHARGE_PROTOCOL_FOLDER_PATH = '../round_raw_data_to_7/out_charge_protocol'

    # .xlsx files
    folders_sheets = {'13. CS2_33': 'Channel_1-006', '14. CS2_34': 'Channel_1-007', '15. CS2_35': 'Channel_1-008',
                      '16. CS2_36': 'Channel_1-009', '17. CS2_37': 'Channel_1-010', '18. CS2_38': 'Channel_1-011',
                      '19. CX2_33': 'Channel_1-012', '20. CX2_34': 'Channel_1-001', '21. CX2_35': 'Channel_1-002',
                      '22. CX2_36': 'Channel_1-003', '23. CX2_37': 'Channel_1-004', '24. CX2_38': 'Channel_1-005'}

    # Define limits Vl and Vh to extract segments of voltage curve during CC charge protocol
    voltage_high_limit = 4.2
    voltage_delta = 0.3
    voltage_low_limit = voltage_high_limit - voltage_delta

    # Multiply by 1000
    # voltage_high_limit = convert_to_milli_and_round_to_3_signs(voltage_high_limit)
    # voltage_delta = convert_to_milli_and_round_to_3_signs(voltage_delta)
    # voltage_low_limit = convert_to_milli_and_round_to_3_signs(voltage_low_limit)

    # Define limits Il and Ih extract segments of the current curve during CV charge protocol
    for file in folders_sheets:
        match = re.search(r'S', file)
        if match:
            charge_c_rate = 0.55  # CS2_, equal to the charge C-rate, here are Amperes for 0.5C-rate
        else:
            charge_c_rate = 0.675  # CX2_, equal to the charge C-rate, here are Amperes for 0.5C-rate

    current_high_limit = charge_c_rate
    current_low_limit = 0.6 * current_high_limit

    # Multiply by 1000
    # charge_c_rate = convert_to_milli_and_round_to_3_signs(charge_c_rate)
    # current_high_limit = convert_to_milli_and_round_to_3_signs(current_high_limit)
    # current_low_limit = convert_to_milli_and_round_to_3_signs(current_low_limit)

    # CS2_, CX2_ batteries (.xlsx files)
    for folder, sheet_name in list(folders_sheets.items())[:]:  # заходим в папку с батарейкой
        battery_folder_path = os.path.join(GROUP_1_RAW_DATA_FOLDER_PATH, folder)
        onlyfiles = []
        file_names = []
        for f in listdir(battery_folder_path):  # составляем list of file names in the folder
            if isfile(join(battery_folder_path, f)):  # если это файл, то клади его в список onlyfiles
                file_names.append(f)
                onlyfiles.append(join(battery_folder_path,
                                      f))  # получился список onlyfiles всех путей до всех файлов в папке для конкретной батарейки

        # Create folders for batteries in the output folder if they haven't been created before
        parent_directory = GROUP_1_OUT_CHARGE_PROTOCOL_FOLDER_PATH
        directory = folder
        path = os.path.join(parent_directory, directory)
        os.makedirs(path)

        # Для каждого файла в папке с батарейкой:
        # Extract segments (data) in files for each battery
        for i in range(len(onlyfiles)):
            battery_data = pd.DataFrame(pd.read_excel(onlyfiles[i], sheet_name))
            curr_file_name = file_names[i][:-5]
            # Extract charge protocol and specific segments of current and voltage for each battery
            process_data(battery_data)




    # .mat files
    # mat_format_batteries = ['25. PL11', '26. PL13', '5. B0028', '6. B0027', '7. B0026', '8. B0025', '9. B0018',
    #                         '10. B0007', '11. B0006', '12. B0005', '27. RW1', '28.RW2', '29.RW3', '30. RW4', '31. RW5',
    #                         '32. RW6',
    #                         '33. RW7', '34. RW8', '35. RW9', '36. RW10', '37. RW11', '38. RW12', '39. RW13', '40. RW14',
    #                         '41. RW15', '42. RW16', '43. RW20', '44. RW21', '45. RW22', '46. RW23', '47. RW24',
    #                         '48. RW25', '49. RW26', '50. RW27', '51. RW28']

    # PL, RW and B batteries (.mat files)
    # for folder_with_mat in range(len(mat_format_batteries))[2:3]:
    #     battery_folder_path = os.path.join(GROUP_1_RAW_DATA_FOLDER_PATH, mat_format_batteries[folder_with_mat])
    #     onlyfiles = []
    #     file_names = []
    #     for f in listdir(battery_folder_path):  # составляем list of file names in the folder
    #         if isfile(join(battery_folder_path, f)):  # если это файл, то клади его в список onlyfiles
    #             file_names.append(f)
    #             onlyfiles.append(join(battery_folder_path,
    #                                   f))  # получился список onlyfiles всех путей до всех файлов в папке для конкретной батарейки

        # Create folders for batteries in the output folder if they haven't been created before
        # parent_directory = GROUP_1_OUT_CHARGE_PROTOCOL_FOLDER_PATH
        # directory = mat_format_batteries[folder_with_mat]
        # path = os.path.join(parent_directory, directory)
        # os.makedirs(path)

        # Для каждого файла в папке с батарейкой:
        # for i in range(len(onlyfiles)):
        #     # read .mat files of batteries
        #     curr_file_name = file_names[i][:-4]
        #     battery_data_mat = scipy.io.loadmat(onlyfiles[i])[curr_file_name]
        #     # print(battery_data_mat)
        #     all_measurements = battery_data_mat[0][0][0][0]
        #     charge_filter = list(i[0][0] == 'charge' for i in all_measurements)
        #     charge_measurements = all_measurements[charge_filter]
        #     discharge_filter = list(i[0][0] == 'discharge' for i in all_measurements)
        #     discharge_measurements = all_measurements[discharge_filter]
        #     impedance_filter = list(i[0][0] == 'impedance' for i in all_measurements)
        #     impedance_measurements = all_measurements[impedance_filter]

            # Extract charge protocol and specific segments of current and voltage for each battery
            # process_data(battery_data_df)
