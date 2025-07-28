import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.svm import SVR
import seaborn as sns
from sklearn.linear_model import RANSACRegressor

# DATA_FOLDER = '../features'
# OUTPUT_FOLDER = '../features_without_outliers'
# Round to 3
# DATA_FOLDER = '../round_raw_data_to_3/features'
# OUTPUT_FOLDER = '../round_raw_data_to_3/features_without_outliers'
# Round to 4
# DATA_FOLDER = '../round_raw_data_to_4/features'
# OUTPUT_FOLDER = '../round_raw_data_to_4/features_without_outliers'
#Multiply by 1000
# DATA_FOLDER = '../multiply_raw_data_by_1000/features'
# OUTPUT_FOLDER = '../multiply_raw_data_by_1000/features_without_outliers'
# Round to 5
# DATA_FOLDER = '../round_raw_data_to_5/features'
# OUTPUT_FOLDER = '../round_raw_data_to_5/features_without_outliers'
# Round to 7
DATA_FOLDER = '../round_raw_data_to_7/features'
OUTPUT_FOLDER = '../round_raw_data_to_7/features_without_outliers'

def build_polynomial(X, y):
    # Build polynomial using poly1d
    poly_fit = np.poly1d(np.polyfit(X.tolist(), y.tolist(), 9))
    plt.plot(X, poly_fit(X), c='r', markersize=5, label='polynomial')
    return poly_fit

# Data preprocessing. Remove outliers in the training data only!
# Erroneous Capacity from Cycle to Cycle should be removed
if __name__ == "__main__":
    file_names = ['CX2_33_features.csv', 'CX2_35_features.csv', 'CX2_36_features.csv', 'CS2_33_features.csv', 'CS2_34_features.csv', 'CS2_35_features.csv']
    for file in file_names[1:]:
        file_name_for_save = file[:-4]
        data = pd.read_csv(os.path.join(DATA_FOLDER, file)) # read data
        cycle_indexes = data['Cycle_Index'].unique()  # unique cycle indexes
        capacities = {}
        for i in cycle_indexes:
            curr_cycle = data.loc[(data['Cycle_Index'] == i) & (data['Step_Index'] == 2)] # cut one cycle
            # curr_cycle = data.loc[data['Cycle_Index'] == i] # cut one cycle
            curr_cycle = curr_cycle.reset_index(drop=True)
            if len(curr_cycle) == 0:
                continue
            # step_2 = curr_cycle.loc[curr_cycle['Step_Index'] == 2]
            # step_2 = step_2.reset_index(drop=True)
            # capacity_for_step_2 = step_2['Capacity_Ah'][len(step_2) - 1]
            # step_4 = curr_cycle.loc[curr_cycle['Step_Index'] == 4]
            # step_4 = step_4.reset_index(drop=True)
            # capacity_for_step_4 = step_4['Capacity_Ah'][len(step_4) - 1]
            # full_capacity = capacity_for_step_2 + capacity_for_step_4
            capacities[i] = curr_cycle['Capacity_Ah'][len(curr_cycle)-1]
            # capacities[i] = full_capacity

        X = np.array(list(capacities.keys())).reshape(-1) # X = 'Cycle_Index'
        y = np.array(list(capacities.values())).reshape(-1) # y = 'Capacity_Ah'

        # Build polynomial
        plt.figure(figsize=(10, 10))
        plt.scatter(X, y, color='blue', label='y')
        polynomial_fun = build_polynomial(X, y)
        y_polynomial = polynomial_fun(X)

        # Define threshold
        threshold = 0.025
        indexes_to_delete = []
        for i in range(len(y)):
            if np.abs(y[i] - y_polynomial[i]) > threshold:
                indexes_to_delete.append(i)
        y_res = np.delete(y, indexes_to_delete)
        X_res = np.delete(X, indexes_to_delete) # остались номера цилков X, совершенно разные
        print("Amount of outliers is ", len(indexes_to_delete))
        plt.scatter(X_res, y_res, color='green', label='y_res')
        plt.show()

        data_indexes_to_delete = list(map(lambda x: x+1, indexes_to_delete)) # или можно так: увеличение индексов на 1 для data
        data = data[data['Cycle_Index'].isin(X_res)] # или можно так: # data = data[~data['Cycle_Index'].isin(data_indexes_to_delete)]
        data_without_outliers_name = os.path.join(OUTPUT_FOLDER, file_name_for_save + '_wo_outliers.csv')
        data.to_csv(data_without_outliers_name, index=False)

