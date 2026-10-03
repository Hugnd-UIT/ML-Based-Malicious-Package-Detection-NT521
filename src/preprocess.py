import os
import numpy as np
import pandas as pd
from sklearn.preprocessing import OrdinalEncoder

sys_path = os.path.dirname(os.path.abspath(__file__))
from extract import FEATURES

BASE = os.path.dirname(sys_path)
TRAIN_PATH = os.path.join(BASE, "dataset", "train.csv")

CAT_COLS = [
    "State_Transition",
    "Read_Processes",
    "Write_Processes",
    "Read_Data_Transfer_Processes",
    "Write_Data_Transfer_Processes",
    "File_Access_Processes",
    "Total_Dependencies",
    "Direct_Dependencies",
    "Indirect_Dependencies",
    "Pattern_1",
    "Pattern_2",
    "Pattern_3",
    "Pattern_4",
    "Pattern_5",
    "Pattern_6",
    "Pattern_7",
    "Pattern_8",
    "Pattern_9",
    "Pattern_10"
]

_encoder = None


def fit():
    global _encoder
    if _encoder is None:
        train = pd.read_csv(TRAIN_PATH, usecols=CAT_COLS)
        _encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
        _encoder.fit(train[CAT_COLS].fillna("").astype(str))
    return _encoder


def transform(df):
    enc = fit()
    data = df.copy()
    for col in CAT_COLS:
        if col in data.columns:
            data[col] = data[col].fillna("").astype(str)
        else:
            data[col] = ""
    data[CAT_COLS] = enc.transform(data[CAT_COLS])
    for col in FEATURES:
        if col not in data.columns:
            data[col] = 0
    return data[FEATURES].astype(np.float32)


if __name__ == "__main__":
    enc = fit()