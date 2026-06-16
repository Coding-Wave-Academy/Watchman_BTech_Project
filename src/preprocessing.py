import os
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder
import joblib
from src.logger import logger as log

# ─────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────

DATA_PATH       = 'data/raw/CICIDS-2017/'
PROCESSED_PATH  = 'data/processed/'
MODEL_PATH      = 'models/'
LABEL_COLUMN    = 'Label'

LABEL_MAPPING = {
    'BENIGN'           : 'Normal',
    'PortScan'         : 'PortScan',
    'DoS Hulk'         : 'DoS',
    'DoS GoldenEye'    : 'DoS',
    'DoS slowloris'    : 'DoS',
    'DoS Slowhttptest' : 'DoS',
    'DDoS'             : 'DoS',
    'FTP-Patator'      : 'BruteForce',
    'SSH-Patator'      : 'BruteForce',
    'Bot'              : 'Anomaly',
    'Infiltration'     : 'Anomaly',
    'Heartbleed'       : 'Anomaly',
}

# ─────────────────────────────────────────────────────────────
# MODULE 1 — Load all CSV files
# ─────────────────────────────────────────────────────────────

def load_datasets(data_path):
    """Load and combine all CICIDS2017 CSV files."""
    log.info("\n[MODULE 1] Loading datasets...")

    files = [f for f in os.listdir(data_path) if f.endswith('.csv')]
    log.info(f"  Files found: {len(files)}")

    dfs = []
    for f in files:
        temp = pd.read_csv(os.path.join(data_path, f), low_memory=False)
        log.info(f"  Loaded {f}: {temp.shape}")
        dfs.append(temp)

    df = pd.concat(dfs, ignore_index=True)
    log.info(f"\n  Combined shape: {df.shape}")
    return df

# ─────────────────────────────────────────────────────────────
# MODULE 2 — Clean column names
# ─────────────────────────────────────────────────────────────

def clean_columns(df):
    """Strip leading/trailing spaces from column names."""
    log.info("\n[MODULE 2] Cleaning column names...")
    df.columns = df.columns.str.strip()
    log.info(f"  Sample columns: {df.columns[:4].tolist()}")
    return df

# ─────────────────────────────────────────────────────────────
# MODULE 3 — Handle infinite and missing values
# ─────────────────────────────────────────────────────────────

def fix_infinite_and_missing(df):
    """Replace inf with NaN then drop affected rows."""
    log.info("\n[MODULE 3] Fixing infinite and missing values...")

    before = len(df)
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    total_nan = df.isnull().sum().sum()
    log.info(f"  Total NaN after inf replacement: {total_nan}")

    df.dropna(inplace=True)
    after = len(df)
    log.info(f"  Rows dropped: {before - after}")
    log.info(f"  Shape after cleaning: {df.shape}")
    return df

# ─────────────────────────────────────────────────────────────
# MODULE 4 — Map labels to project categories
# ─────────────────────────────────────────────────────────────

def map_labels(df, label_column=LABEL_COLUMN):
    """Map original CICIDS2017 labels to 5 project categories."""
    log.info("\n[MODULE 4] Mapping labels...")

    df[label_column] = df[label_column].map(LABEL_MAPPING)

    unmapped = df[label_column].isnull().sum()
    log.info(f"  Unmapped rows (encoding-corrupted Web Attack labels): {unmapped}")
    log.info(f"  Percentage of total data: {unmapped/len(df)*100:.3f}% — safe to drop")

    before = len(df)
    df.dropna(subset=[label_column], inplace=True)
    after = len(df)
    log.info(f"  Dropped: {before - after} rows")

    log.info("\n  Final class distribution:")
    log.info(df[label_column].value_counts().to_string())
    return df

# ─────────────────────────────────────────────────────────────
# MODULE 5 — Encode labels and save CLEAN data
# ─────────────────────────────────────────────────────────────

def encode_and_save(df, label_column, processed_path, model_path):
    """
    Encode string labels to integers.
    Save CLEAN UNBALANCED dataset.
    SMOTE balancing is intentionally deferred to train.py
    to prevent data leakage into the test set.
    """
    log.info("\n[MODULE 5] Encoding labels and saving...")

    os.makedirs(processed_path, exist_ok=True)
    os.makedirs(model_path, exist_ok=True)

    le = LabelEncoder()
    df = df.copy()
    df[label_column] = le.fit_transform(df[label_column])

    log.info(f"  Label encoding map:")
    for i, cls in enumerate(le.classes_):
        log.info(f"    {i} → {cls}")

    encoder_path = os.path.join(model_path, 'label_encoder.pkl')
    joblib.dump(le, encoder_path)
    log.info(f"\n  Encoder saved: {encoder_path}")

    output_path = os.path.join(processed_path, 'cicids2017_processed.csv')
    df.to_csv(output_path, index=False)
    log.info(f"  Clean data saved: {output_path}")
    log.info(f"  Shape: {df.shape}")
    log.info(f"\n  NOTE: SMOTE applied in train.py after train/test split.")

    return df, le

# ─────────────────────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────────────────────

def run_pipeline():
    log.info("=" * 60)
    log.info("  NIDS PREPROCESSING PIPELINE — CICIDS2017")
    log.info("=" * 60)

    df = load_datasets(DATA_PATH)
    df = clean_columns(df)
    df = fix_infinite_and_missing(df)
    df = map_labels(df)
    df, le = encode_and_save(df, LABEL_COLUMN, PROCESSED_PATH, MODEL_PATH)

    log.info("\n" + "=" * 60)
    log.info("  PREPROCESSING COMPLETE")
    log.info("=" * 60)

    return df, le


if __name__ == '__main__':
    run_pipeline()