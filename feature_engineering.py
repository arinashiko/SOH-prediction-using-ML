import os
import sys
from os import listdir
import numpy as np
import pandas as pd
from frechetdist import frdist
from scipy.interpolate import InterpolatedUnivariateSpline
from scipy.spatial.distance import directed_hausdorff
from scipy.stats import entropy
from scipy.stats import skew, kurtosis
from typing import Tuple
import re

sys.setrecursionlimit(5000)


def filter_cycles(dfr: pd.DataFrame):
    cycle_indexes = dfr['Cycle_Index'].unique()
    for j in cycle_indexes:
        cc_step_curr_cycle = dfr.loc[(dfr['Cycle_Index'] == j) & (dfr['Step_Index'] == 2)]
        cv_step_curr_cycle = dfr.loc[(dfr['Cycle_Index'] == j) & (dfr['Step_Index'] == 4)]
        if (len(cc_step_curr_cycle) == 0) or (len(cv_step_curr_cycle) == 0):
            dfr = dfr[dfr['Cycle_Index'] != j]
    return dfr.reset_index(drop=True)

# CC step
def compute_cc_stats(df: pd.DataFrame):
    global nominal_capacity
    cycle_indexes = df['Cycle_Index'].unique()
    for cycle_index in cycle_indexes:
        curr_cycle_step_index_rows = df.loc[(df['Cycle_Index'] == cycle_index) & (df['Step_Index'] == 2)]
        if (len(curr_cycle_step_index_rows) == 0):
            continue

        hausdorff_cc, frechet_cc, sh_entropy_cc, slope_voltage_cc = compute_Hausdorff_Frechet_Sh_entropy_Slope_CC(curr_cycle_step_index_rows)
        mean_current_cc = np.mean(curr_cycle_step_index_rows['Current(A)'])
        skewness_cc = skew(curr_cycle_step_index_rows['Voltage(V)'], axis=0, bias=True)
        kurtosis_cc = kurtosis(curr_cycle_step_index_rows['Voltage(V)'], axis=0, bias=True)
        capacity_for_each_row, energy_for_each_row, charge_time_for_each_row = compute_Capacity_Energy_Charge_Time_CC(curr_cycle_step_index_rows)

        # SOH вычисляется на Step_Index = 2
        if (cycle_index == 1):
            nominal_capacity = list(capacity_for_each_row.values())[-1]
            full_capacity = nominal_capacity
        else:
            full_capacity = list(capacity_for_each_row.values())[-1]
        soh = full_capacity / nominal_capacity

        df.loc[(df['Cycle_Index'] == cycle_index) & (df['Step_Index'] == 2), 'Hausdorff_distance'] = hausdorff_cc
        df.loc[(df['Cycle_Index'] == cycle_index) & (df['Step_Index'] == 2), 'Frechet_distance'] = frechet_cc
        df.loc[(df['Cycle_Index'] == cycle_index) & (df['Step_Index'] == 2), 'Shannon_entropy'] = sh_entropy_cc[0]  # chto eto [0]
        df.loc[(df['Cycle_Index'] == cycle_index) & (df['Step_Index'] == 2), 'Signal_mean'] = mean_current_cc
        df.loc[(df['Cycle_Index'] == cycle_index) & (df['Step_Index'] == 2), 'Skewness'] = skewness_cc
        df.loc[(df['Cycle_Index'] == cycle_index) & (df['Step_Index'] == 2), 'Kurtosis'] = kurtosis_cc
        df.loc[(df['Cycle_Index'] == cycle_index) & (df['Step_Index'] == 2), 'Slope'] = slope_voltage_cc # Slope_CCCV_CCCT
        df.loc[df['Cycle_Index'] == cycle_index, 'SOH'] = soh
        for k, v in capacity_for_each_row.items():
            df.iloc[k, df.columns.get_loc('Capacity_Ah')] = v
        for k, v in energy_for_each_row.items():
            df.iloc[k, df.columns.get_loc('Energy_Wh')] = v
        for k, v in charge_time_for_each_row.items():
            df.iloc[k, df.columns.get_loc('Charge_Time_s')] = v


def compute_Hausdorff_Frechet_Sh_entropy_Slope_CC(curr_cycle_step_index_rows):
    initial_row = curr_cycle_step_index_rows.iloc[0]
    end_row = curr_cycle_step_index_rows.iloc[-1]
    x1 = initial_row['Test_Time_Norm_CC']  # Test_Time(s) в начале Step_Index
    x2 = end_row['Test_Time_Norm_CC']  # Test_Time(s) в конце Step_Index
    y1 = initial_row['Voltage_Norm_CC']  # Voltage(V) в начале Step_Index
    y2 = end_row['Voltage_Norm_CC']  # Voltage(V) в конце Step_Index
    k = (y2-y1) / (x2-x1)
    b = y2-k*x2
    reference_line = {}
    for j in curr_cycle_step_index_rows.index:  # from the beginning to the end of a step
        equation = k*curr_cycle_step_index_rows['Test_Time_Norm_CC'][j] + b
        reference_line[curr_cycle_step_index_rows['Test_Time_Norm_CC'][j]] = equation
    reference_line_transformed = np.array(list(reference_line.items()))
    # Real curve
    real_curve = curr_cycle_step_index_rows[['Test_Time_Norm_CC', 'Voltage_Norm_CC']]
    real_curve_transformed = real_curve.to_numpy()
    hausdorff = directed_hausdorff(real_curve_transformed, reference_line_transformed)[0]
    frechet = frdist(real_curve_transformed, reference_line_transformed)
    sh_entropy = entropy(real_curve_transformed, reference_line_transformed, base=base)
    slope_voltage = k
    return hausdorff, frechet, sh_entropy, slope_voltage

def compute_Capacity_Energy_Charge_Time_CC(curr_cycle_step_index_rows) -> Tuple[dict, dict, dict]:  # return 3 values
    capacities = {}
    energies = {}
    charge_times = {}
    initial_index = curr_cycle_step_index_rows.index.values[0]
    current_capacity = 0
    current_energy = 0
    charge_time = 0
    capacities[initial_index] = current_capacity
    energies[initial_index] = current_energy
    charge_times[initial_index] = charge_time
    initial_row = curr_cycle_step_index_rows.iloc[0]
    test_time_initial = initial_row['Test_Time(s)']
    current_initial = initial_row['Current(A)']
    voltage_initial = initial_row['Voltage(V)']
    charge_time_initial = initial_row['Test_Time(s)']
    for cycle_step_row_index in curr_cycle_step_index_rows.index[1:]:  # go through each row, index - индексы глобального массива result_df
        t1 = test_time_initial  # Test_Time(s) of previous step
        t2 = curr_cycle_step_index_rows['Test_Time(s)'][cycle_step_row_index]  # Test_Time(s) of current step
        time = [t1, t2]  # in sec
        c1 = current_initial  # Current(A) of previous step
        c2 = curr_cycle_step_index_rows['Current(A)'][cycle_step_row_index]  # Current(A) of current step
        current = [c1, c2]
        v1 = voltage_initial  # Voltage(V) of previous step
        v2 = curr_cycle_step_index_rows['Voltage(V)'][cycle_step_row_index]  # Voltage(V) of current step
        c1_v1 = c1 * v1
        c2_v2 = c2 * v2
        current_mult_by_voltage = [c1_v1, c2_v2]

        capacity = InterpolatedUnivariateSpline(time, current, k=1)  # Q = I*t [Ah]
        capacity_for_test_time = capacity.integral(t1, t2) / 3600  # in hours, for each test time
        current_capacity = current_capacity + capacity_for_test_time

        e = InterpolatedUnivariateSpline(time, current_mult_by_voltage, k=1)
        energy_for_test_time = e.integral(t1, t2) / 3600  # Wh
        current_energy = current_energy + energy_for_test_time

        test_time_initial = t2
        current_initial = c2
        voltage_initial = v2

        capacities[cycle_step_row_index] = current_capacity
        energies[cycle_step_row_index] = current_energy

        charge_time = t2 - charge_time_initial
        charge_times[cycle_step_row_index] = charge_time

    return capacities, energies, charge_times


## CV step
def compute_cv_stats(df: pd.DataFrame):
    cycle_indexes = df['Cycle_Index'].unique()  # уникальные индексы циклов
    for cycle_index in cycle_indexes:
        curr_cycle_step_index_rows = df.loc[(df['Cycle_Index'] == cycle_index) & (df['Step_Index'] == 4)]
        if (len(curr_cycle_step_index_rows) == 0):
            continue

        hausdorff_cv, frechet_cv, sh_entropy_cv, slope_current_cv = compute_Hausdorff_Frechet_Sh_entropy_Slope_CV(curr_cycle_step_index_rows)
        mean_voltage_cv = np.mean(curr_cycle_step_index_rows['Voltage(V)'])
        skewness_cv = skew(curr_cycle_step_index_rows['Current(A)'], axis=0, bias=True)
        kurtosis_cv = kurtosis(curr_cycle_step_index_rows['Current(A)'], axis=0, bias=True)
        capacity_for_each_row, energy_for_each_row, charge_time_for_each_row = compute_Capacity_Energy_Charge_Time_CV(curr_cycle_step_index_rows)

        df.loc[(df['Cycle_Index'] == cycle_index) & (df['Step_Index'] == 4), 'Hausdorff_distance'] = hausdorff_cv
        df.loc[(df['Cycle_Index'] == cycle_index) & (df['Step_Index'] == 4), 'Frechet_distance'] = frechet_cv
        df.loc[(df['Cycle_Index'] == cycle_index) & (df['Step_Index'] == 4), 'Shannon_entropy'] = sh_entropy_cv[0]
        df.loc[(df['Cycle_Index'] == cycle_index) & (df['Step_Index'] == 4), 'Signal_mean'] = mean_voltage_cv
        df.loc[(df['Cycle_Index'] == cycle_index) & (df['Step_Index'] == 4), 'Skewness'] = skewness_cv
        df.loc[(df['Cycle_Index'] == cycle_index) & (df['Step_Index'] == 4), 'Kurtosis'] = kurtosis_cv
        df.loc[(df['Cycle_Index'] == cycle_index) & (df['Step_Index'] == 4), 'Slope'] = slope_current_cv # Slope_CVCC_CVCT
        for k, v in capacity_for_each_row.items():
            df.iloc[k, df.columns.get_loc('Capacity_Ah')] = v
        for k, v in energy_for_each_row.items():
            df.iloc[k, df.columns.get_loc('Energy_Wh')] = v
        for k, v in charge_time_for_each_row.items():
            df.iloc[k, df.columns.get_loc('Charge_Time_s')] = v

def compute_Hausdorff_Frechet_Sh_entropy_Slope_CV(curr_cycle_step_index_rows):
    initial_row = curr_cycle_step_index_rows.iloc[0]
    end_row = curr_cycle_step_index_rows.iloc[-1]
    x1 = initial_row['Test_Time_Norm_CV']  # Test_Time(s) в начале step
    x2 = end_row['Test_Time_Norm_CV']  # Test_Time(s) в конце step
    y1 = initial_row['Current_Norm_CV']  # Voltage(V) в начале step
    y2 = end_row['Current_Norm_CV']  # Voltage(V) в конце step
    k = (y2 - y1)/(x2 - x1)
    b = y2 - k * x2
    reference_line = {}
    for j in curr_cycle_step_index_rows.index:  # from the beginning to the end of a step
        equation = k * curr_cycle_step_index_rows['Test_Time_Norm_CV'][j] + b
        reference_line[curr_cycle_step_index_rows['Test_Time_Norm_CV'][j]] = equation
    reference_line_transformed = np.array(list(reference_line.items()))
    # Real curve
    real_curve = curr_cycle_step_index_rows[['Test_Time_Norm_CV', 'Current_Norm_CV']]
    real_curve_transformed = real_curve.to_numpy()
    hausdorff = directed_hausdorff(real_curve_transformed, reference_line_transformed)[0]
    frechet = frdist(real_curve_transformed, reference_line_transformed)
    sh_entropy = entropy(real_curve_transformed, reference_line_transformed, base=base)
    slope_current = k
    return hausdorff, frechet, sh_entropy, slope_current

def compute_Capacity_Energy_Charge_Time_CV(curr_cycle_step_index_rows) -> Tuple[dict, dict, dict]:  # return 3 values
    capacities = {}
    energies = {}
    charge_times = {}
    initial_index = curr_cycle_step_index_rows.index.values[0]
    current_capacity = 0
    current_energy = 0
    charge_time = 0
    capacities[initial_index] = current_capacity
    energies[initial_index] = current_energy
    charge_times[initial_index] = charge_time
    initial_row = curr_cycle_step_index_rows.iloc[0]
    test_time_initial = initial_row['Test_Time(s)']
    current_initial = initial_row['Current(A)']
    voltage_initial = initial_row['Voltage(V)']
    charge_time_initial = initial_row['Test_Time(s)']
    for cycle_step_row_index in curr_cycle_step_index_rows.index[1:]:  # go through each row, index - индексы глобального массива result_df
        t1 = test_time_initial  # Test_Time(s) of previous step
        t2 = curr_cycle_step_index_rows['Test_Time(s)'][cycle_step_row_index]  # Test_Time(s) of current step
        time = [t1, t2]  # in sec
        c1 = current_initial  # Current(A) of previous step
        c2 = curr_cycle_step_index_rows['Current(A)'][cycle_step_row_index]  # Current(A) of current step
        current = [c1, c2]
        v1 = voltage_initial  # Voltage(V) of previous step
        v2 = curr_cycle_step_index_rows['Voltage(V)'][cycle_step_row_index]  # Voltage(V) of current step
        c1_v1 = c1 * v1
        c2_v2 = c2 * v2
        current_mult_by_voltage = [c1_v1, c2_v2]

        capacity = InterpolatedUnivariateSpline(time, current, k=1)  # Q = I*t [Ah]
        capacity_for_test_time = capacity.integral(t1, t2) / 3600  # in hours, for each test time
        current_capacity = current_capacity + capacity_for_test_time

        e = InterpolatedUnivariateSpline(time, current_mult_by_voltage, k=1)  # E=P*t=U*I*t
        energy_for_test_time = e.integral(t1, t2) / 3600  # Wh
        current_energy = current_energy + energy_for_test_time

        test_time_initial = t2
        current_initial = c2
        voltage_initial = v2

        capacities[cycle_step_row_index] = current_capacity
        energies[cycle_step_row_index] = current_energy

        charge_time = t2 - charge_time_initial
        charge_times[cycle_step_row_index] = charge_time

    return capacities, energies, charge_times


if __name__ == "__main__":
    # INPUT_FOLDER = '../merged'
    # OUTPUT_FOLDER = '../features'
    # Round to 3
    # INPUT_FOLDER = '../round_raw_data_to_3/merged'
    # OUTPUT_FOLDER = '../round_raw_data_to_3/features'
    # Round to 4
    # INPUT_FOLDER = '../round_raw_data_to_4/merged'
    # OUTPUT_FOLDER = '../round_raw_data_to_4/features'
    # Multiply by 1000
    # INPUT_FOLDER = '../multiply_raw_data_by_1000/merged'
    # OUTPUT_FOLDER = '../multiply_raw_data_by_1000/features'
    # Round to 5
    INPUT_FOLDER = '../round_raw_data_to_5/merged'
    OUTPUT_FOLDER = '../round_raw_data_to_5/features'
    # Round to 7
    INPUT_FOLDER = '../round_raw_data_to_7/merged'
    OUTPUT_FOLDER = '../round_raw_data_to_7/features'

    base = 2

    for file in listdir(INPUT_FOLDER)[:]:
        dataset_path = os.path.join(INPUT_FOLDER, file)  # one battery
        dataset = pd.read_csv(dataset_path, delimiter=",")
        df = pd.DataFrame(dataset)
        file_name = file[:-11]

        # Create new columns
        result_df_prev = df.copy().assign(
            Capacity_Ah=None, Energy_Wh=None, Hausdorff_distance=None,
            Frechet_distance=None,
            Shannon_entropy=None, Signal_mean=None,
            Skewness=None, Kurtosis=None,
            Slope=None,
            Charge_Time_s=None,
            SOH=None,
            Energy_diff_between_CCCV_and_CVCC=None, Energy_ratio_CCCV_div_CVCC=None)
        # Drop unused columns
        columns_to_drop = ['Data_Point', 'Date_Time', 'Step_Time(s)',
                           'Is_FC_Data', 'AC_Impedance(Ohm)', 'ACI_Phase_Angle(Deg)']
        result_df_dropped_col = result_df_prev.drop(columns_to_drop, axis=1)

        # Preliminary sort by columns 'Cycle_Index', then by 'Step_Index'
        result_df = result_df_dropped_col.sort_values(by=['Cycle_Index', 'Step_Index'])
        # Filter cycles - check if there are both CC and CV steps
        result_df = filter_cycles(result_df)

        match = re.search(r'S', file)
        if match:
            # Make 30 sec time step of data for 1 cycles for CS2_ batteries
            result_df_dropped_col = result_df_dropped_col.drop(list(filter(lambda x: x % 3 != 0, result_df_dropped_col[
            result_df_dropped_col['Cycle_Index'] == 1].index.values)))
            # Battery specific data for CS2_ battery
            result_df['Charge_Current_A'] = 0.55
            # result_df['Charge_Current_A'] = 550 # mAh
            result_df['Discharge_Current_A'] = 0.55
            # result_df['Discharge_Current_A'] = 550 # mAh
            nominal_capacity = 1.1
            result_df['Nominal_Capacity_Ah'] = nominal_capacity  # Ah
        else:
            # Battery specific data for CX2_ battery
            result_df['Charge_Current_A'] = 0.675  # A, 0.5C-rate
            # result_df['Charge_Current_A'] = 675  # mA, 0.5C-rate
            result_df['Discharge_Current_A'] = 0.675  # A, 0.5C-rate
            # result_df['Discharge_Current_A'] = 675  # mA, 0.5C-rate
            nominal_capacity = 1.35
            result_df['Nominal_Capacity_Ah'] = nominal_capacity  # Ah


        # Calculate features
        compute_cc_stats(result_df)
        compute_cv_stats(result_df)

        # Calculation of 'Energy_difference' and 'Energy_ratio between' CCCV-CCCT and CVCC-CVCT
        cycle_indexes_result_df = result_df['Cycle_Index'].unique()  # unique cycle indexes
        for i in cycle_indexes_result_df:
            curr_cycle_index_rows = result_df.loc[(result_df['Cycle_Index'] == i)]
            curr_cycle_index_rows = curr_cycle_index_rows.reset_index(drop=True)
            energy_cc = curr_cycle_index_rows[curr_cycle_index_rows['Step_Index'] == 2].iloc[-1]['Energy_Wh']
            energy_cv = curr_cycle_index_rows[curr_cycle_index_rows['Step_Index'] == 4].iloc[-1]['Energy_Wh']
            if energy_cv == 0:
                print("Denominator is zero")
            else:
                energy_ratio = energy_cc / energy_cv
                result_df.loc[(result_df['Cycle_Index'] == i), 'Energy_ratio_CCCV_div_CVCC'] = energy_ratio
            energy_diff = energy_cc - energy_cv
            result_df.loc[(result_df['Cycle_Index'] == i), 'Energy_diff_between_CCCV_and_CVCC'] = energy_diff

        # Columns to drop after feature engineering is completed
        col_to_drop = ['Test_Time_Norm_CV', 'Current_Norm_CV', 'Test_Time_Norm_CC', 'Voltage_Norm_CC']
        result_df_col_to_drop = result_df.drop(col_to_drop, axis=1)

        # Save result_df
        result_df_name = os.path.join(OUTPUT_FOLDER, file_name + '_features.csv')
        result_df_col_to_drop.to_csv(result_df_name, index=False)
