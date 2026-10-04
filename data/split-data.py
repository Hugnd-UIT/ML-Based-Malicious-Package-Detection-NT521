import gc
import os
import time
import pandas as pd
import numpy as np

BASE = (
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if '__file__' in globals()
    else os.path.abspath('.')
)

INPUT = os.path.join(BASE, 'dataset', 'QUT-DV25.csv')

if not os.path.exists(INPUT):
    raise FileNotFoundError(f"[!] Input file not found: {INPUT}")

TRAIN = os.path.join(BASE, 'dataset', 'train.csv')
VAL = os.path.join(BASE, 'dataset', 'val.csv')
TEST = os.path.join(BASE, 'dataset', 'test.csv')

RANDOM = 3033


def clean(pkg):
    name = str(pkg)
    for ext in ('.tar.gz', '.zip', '.whl', '.tgz', '.tar.bz2'):
        if name.endswith(ext):
            name = name[:-len(ext)]
            break
    parts = name.split('-')
    if len(parts) > 1 and parts[-1] and parts[-1][0].isdigit():
        return '-'.join(parts[:-1]).lower()
    return name.lower()


def partition(frame, target_train, target_val):
    keys_train, keys_val, keys_test = [], [], []
    sum_train, sum_val = 0, 0
    for _, row in frame.iterrows():
        count = row['count']
        key = row['group']
        if sum_train + count <= target_train:
            keys_train.append(key)
            sum_train += count
        elif sum_val + count <= target_val:
            keys_val.append(key)
            sum_val += count
        else:
            keys_test.append(key)
    return keys_train, keys_val, keys_test


def split_data():
    t = time.time()

    print(f"[*] Reading: {os.path.basename(INPUT)}")
    df = pd.read_csv(INPUT)
    print(f"[+] Loaded: {len(df):,} samples | {df.shape[1]} columns")

    df['group'] = df['Package_Name'].map(clean)

    features = [col for col in df.columns if col not in ('Package_Name', 'Level', 'group')]
    df = df.drop_duplicates(subset=features, keep='first')

    groups = df.groupby('group').agg(level=('Level', 'mean'), count=('Level', 'count')).reset_index()
    groups = groups.sample(frac=1.0, random_state=RANDOM).reset_index(drop=True)

    group_zero = groups[groups['level'] <= 0.5]
    group_one = groups[groups['level'] > 0.5]

    total_zero = group_zero['count'].sum()
    total_one = group_one['count'].sum()

    train_zero, val_zero, test_zero = partition(group_zero, total_zero * 0.70, total_zero * 0.15)
    train_one, val_one, test_one = partition(group_one, total_one * 0.70, total_one * 0.15)

    keys_train = set(train_zero + train_one)
    keys_val = set(val_zero + val_one)
    keys_test = set(test_zero + test_one)

    train_df = df[df['group'].isin(keys_train)].drop(columns=['group'])
    val_df = df[df['group'].isin(keys_val)].drop(columns=['group'])
    test_df = df[df['group'].isin(keys_test)].drop(columns=['group'])

    del df, groups
    gc.collect()

    os.makedirs(os.path.dirname(TRAIN), exist_ok=True)
    train_df.to_csv(TRAIN, index=False)
    val_df.to_csv(VAL, index=False)
    test_df.to_csv(TEST, index=False)

    print(f"[+] Train: {TRAIN} ({len(train_df):,} samples)")
    print(f"[+] Val  : {VAL} ({len(val_df):,} samples)")
    print(f"[+] Test : {TEST} ({len(test_df):,} samples)")
    print(f"[+] Completed in {time.time() - t:.2f}s")

    for name, part in [('Train', train_df), ('Val', val_df), ('Test', test_df)]:
        b = (part['Level'] == 0).sum()
        m = (part['Level'] == 1).sum()
        total = len(part)
        print(f"- {name:<5}: {total:>5,} samples | Benign: {b:>5,} ({b/total*100:.2f}%) | Malicious: {m:>5,} ({m/total*100:.2f}%)")

    del train_df, val_df, test_df
    gc.collect()


if __name__ == '__main__':
    split_data()