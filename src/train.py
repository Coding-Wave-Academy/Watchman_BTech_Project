"""
train.py
NIDS + ML + Blockchain Project — BTech
Modular model training pipeline

DESIGN NOTE:
  SMOTE is applied here AFTER the train/test split.
  This ensures the test set contains only real,
  unseen data — no synthetic samples from training.
  This produces honest, academically valid metrics.
"""

import os
import time
from logger import logger as log
import collections
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.ensemble        import RandomForestClassifier, IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.metrics         import (
    accuracy_score, precision_score, recall_score,
    f1_score, confusion_matrix, classification_report
)
from imblearn.over_sampling  import SMOTE
from imblearn.under_sampling import RandomUnderSampler

# ─────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────

PROCESSED_PATH  = 'data/processed/'
MODEL_PATH      = 'models/'
RESULTS_PATH    = 'results/'

PROCESSED_FILE  = 'cicids2017_processed.csv'
LABEL_COLUMN    = 'Label'

RANDOM_STATE    = 42
TEST_SIZE       = 0.2
N_ESTIMATORS    = 100
N_JOBS          = -1

# Balancing applied to TRAINING SET ONLY
# Class encoding (alphabetical): 0=Anomaly | 1=BruteForce | 2=DoS | 3=Normal | 4=PortScan
UNDERSAMPLE_STRATEGY = {
    3: 200000,   # Normal   → 200k
    2: 150000,   # DoS      → 150k
    4: 120000,   # PortScan → 120k (capped below train split count)
}

OVERSAMPLE_STRATEGY = {
    1: 50000,    # BruteForce → 50k
    0: 10000,    # Anomaly    → 10k (small class, conservative SMOTE)
}

# ─────────────────────────────────────────────────────────────
# MODULE 1 — Load processed data
# ─────────────────────────────────────────────────────────────

def load_processed_data(processed_path, filename, label_column):
    """Load the clean unbalanced dataset from preprocessing."""
    log.info("\n[MODULE 1] Loading processed data...")

    filepath = os.path.join(processed_path, filename)
    df = pd.read_csv(filepath)

    le = joblib.load(os.path.join(MODEL_PATH, 'label_encoder.pkl'))

    log.info(f"  Shape: {df.shape}")
    log.info(f"  Class distribution (unbalanced — as expected):")
    counts = df[label_column].value_counts().sort_index()
    for code, count in counts.items():
        label_name = le.classes_[int(code)]
        log.info(f"    {code} ({label_name}): {count:,}")

    X = df.drop(label_column, axis=1)
    y = df[label_column]

    return X, y, le

# ─────────────────────────────────────────────────────────────
# MODULE 2 — Split BEFORE balancing
# ─────────────────────────────────────────────────────────────

def split_data(X, y):
    """
    Split into train and test BEFORE any balancing.
    Test set stays untouched — real data only.
    """
    log.info("\n[MODULE 2] Splitting data (before balancing)...")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size    = TEST_SIZE,
        random_state = RANDOM_STATE,
        stratify     = y
    )

    log.info(f"  Train size : {X_train.shape[0]:,} (will be balanced)")
    log.info(f"  Test size  : {X_test.shape[0]:,}  (real data only — no SMOTE)")

    return X_train, X_test, y_train, y_test

# ─────────────────────────────────────────────────────────────
# MODULE 3 — Balance TRAINING SET ONLY
# ─────────────────────────────────────────────────────────────

def balance_training_set(X_train, y_train):
    """
    Apply SMOTE + undersampling to training set only.
    Test set is never touched.
    """
    log.info("\n[MODULE 3] Balancing training set...")

    log.info(f"  Before: {collections.Counter(y_train)}")

    under = RandomUnderSampler(
        sampling_strategy = UNDERSAMPLE_STRATEGY,
        random_state      = RANDOM_STATE
    )
    X_under, y_under = under.fit_resample(X_train, y_train)
    log.info(f"  After undersampling: {collections.Counter(y_under)}")

    over = SMOTE(
        sampling_strategy = OVERSAMPLE_STRATEGY,
        random_state      = RANDOM_STATE,
        k_neighbors       = 3
    )
    X_balanced, y_balanced = over.fit_resample(X_under, y_under)
    log.info(f"  After SMOTE: {collections.Counter(y_balanced)}")

    return X_balanced, y_balanced

# ─────────────────────────────────────────────────────────────
# MODULE 4 — Train Random Forest
# ─────────────────────────────────────────────────────────────

def train_random_forest(X_train, y_train):
    """Train Random Forest classifier on balanced training data."""
    log.info("\n[MODULE 4] Training Random Forest...")

    rf = RandomForestClassifier(
        n_estimators = N_ESTIMATORS,
        random_state = RANDOM_STATE,
        n_jobs       = N_JOBS,
        class_weight = 'balanced',
        verbose      = 1
    )

    start = time.time()
    rf.fit(X_train, y_train)
    elapsed = time.time() - start

    log.info(f"\n  Training complete in {elapsed:.1f}s")
    return rf

# ─────────────────────────────────────────────────────────────
# MODULE 5 — Train Isolation Forest (anomaly/zero-day layer)
# ─────────────────────────────────────────────────────────────

def train_isolation_forest(X_train, y_train, le):
    """
    Train Isolation Forest on normal traffic only.
    Provides zero-day/unknown attack detection capability.
    Normal class encoded as index of 'Normal' in le.classes_
    """
    log.info("\n[MODULE 5] Training Isolation Forest (anomaly detector)...")

    normal_code = list(le.classes_).index('Normal')
    X_normal = X_train[y_train == normal_code]
    log.info(f"  Training on {len(X_normal):,} normal traffic samples")

    iso = IsolationForest(
        n_estimators  = 100,
        contamination = 0.05,
        random_state  = RANDOM_STATE,
        n_jobs        = N_JOBS
    )

    start = time.time()
    iso.fit(X_normal)
    elapsed = time.time() - start
    log.info(f"  Training complete in {elapsed:.1f}s")

    return iso

# ─────────────────────────────────────────────────────────────
# MODULE 6 — Evaluate on untouched test set
# ─────────────────────────────────────────────────────────────

def evaluate_model(rf, X_test, y_test, le, results_path):
    """
    Evaluate on the untouched real test set.
    Generates all metrics needed for Chapter 5.
    """
    log.info("\n[MODULE 6] Evaluating on real test set...")

    os.makedirs(results_path, exist_ok=True)

    y_pred = rf.predict(X_test)

    accuracy  = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, average='weighted', zero_division=0)
    recall    = recall_score(y_test, y_pred, average='weighted', zero_division=0)
    f1        = f1_score(y_test, y_pred, average='weighted', zero_division=0)

    log.info(f"\n  ── Overall Metrics (on real unseen test data) ──")
    log.info(f"  Accuracy  : {accuracy  * 100:.2f}%")
    log.info(f"  Precision : {precision * 100:.2f}%")
    log.info(f"  Recall    : {recall    * 100:.2f}%")
    log.info(f"  F1-Score  : {f1        * 100:.2f}%")

    log.info(f"\n  ── Per Class Report ──")
    report = classification_report(
        y_test, y_pred,
        target_names = le.classes_,
        zero_division = 0
    )
    log.info(report)

    # Save text report
    report_path = os.path.join(results_path, 'classification_report.txt')
    with open(report_path, 'w') as f:
        f.write("RANDOM FOREST — CLASSIFICATION REPORT\n")
        f.write("Evaluated on real unseen test data (no synthetic samples)\n")
        f.write("=" * 55 + "\n")
        f.write(f"Accuracy  : {accuracy  * 100:.2f}%\n")
        f.write(f"Precision : {precision * 100:.2f}%\n")
        f.write(f"Recall    : {recall    * 100:.2f}%\n")
        f.write(f"F1-Score  : {f1        * 100:.2f}%\n\n")
        f.write(report)
    log.info(f"\n  Report saved: {report_path}")

    # Confusion matrix
    _plot_confusion_matrix(y_test, y_pred, le, results_path)

    # Feature importance
    _plot_feature_importance(rf, X_test, results_path)

    return {
        'accuracy'  : accuracy,
        'precision' : precision,
        'recall'    : recall,
        'f1'        : f1
    }

def _plot_confusion_matrix(y_test, y_pred, le, results_path):
    log.info("\n  Generating confusion matrix...")

    cm = confusion_matrix(y_test, y_pred)
    cm_norm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]

    plt.figure(figsize=(10, 8))
    sns.heatmap(
        cm_norm,
        annot       = True,
        fmt         = '.2f',
        cmap        = 'Blues',
        xticklabels = le.classes_,
        yticklabels = le.classes_
    )
    plt.title('Confusion Matrix — Normalized\n(Evaluated on Real Unseen Test Data)', fontsize=13)
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.tight_layout()

    path = os.path.join(results_path, 'confusion_matrix.png')
    plt.savefig(path, dpi=150)
    plt.close()
    log.info(f"  Saved: {path}")

def _plot_feature_importance(rf, X_test, results_path, top_n=20):
    log.info(f"\n  Generating top {top_n} feature importance plot...")

    importances   = rf.feature_importances_
    feature_names = X_test.columns.tolist()
    indices       = np.argsort(importances)[::-1][:top_n]

    top_features    = [feature_names[i] for i in indices]
    top_importances = importances[indices]

    plt.figure(figsize=(12, 7))
    sns.barplot(x=top_importances, y=top_features, palette='viridis')
    plt.title(f'Top {top_n} Feature Importances — Random Forest', fontsize=13)
    plt.xlabel('Importance Score')
    plt.tight_layout()

    path = os.path.join(results_path, 'feature_importance.png')
    plt.savefig(path, dpi=150)
    plt.close()
    log.info(f"  Saved: {path}")

# ─────────────────────────────────────────────────────────────
# MODULE 7 — Save models
# ─────────────────────────────────────────────────────────────

def save_models(rf, iso, model_path):
    """Save both trained models for use in the detection pipeline."""
    log.info("\n[MODULE 7] Saving models...")

    os.makedirs(model_path, exist_ok=True)

    rf_path  = os.path.join(model_path, 'random_forest.pkl')
    iso_path = os.path.join(model_path, 'isolation_forest.pkl')

    joblib.dump(rf,  rf_path)
    joblib.dump(iso, iso_path)

    log.info(f"  Random Forest saved    : {rf_path}  ({os.path.getsize(rf_path)/1e6:.1f} MB)")
    log.info(f"  Isolation Forest saved : {iso_path} ({os.path.getsize(iso_path)/1e6:.1f} MB)")

# ─────────────────────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────────────────────

def run_training():
    log.info("=" * 60)
    log.info("  NIDS TRAINING PIPELINE")
    log.info("=" * 60)

    # Module 1: Load clean unbalanced data
    X, y, le = load_processed_data(PROCESSED_PATH, PROCESSED_FILE, LABEL_COLUMN)

    # Module 2: Split FIRST — test set stays untouched
    X_train, X_test, y_train, y_test = split_data(X, y)

    # Module 3: Balance training set only
    X_train_bal, y_train_bal = balance_training_set(X_train, y_train)

    # Module 4: Train Random Forest on balanced training data
    rf = train_random_forest(X_train_bal, y_train_bal)

    # Module 5: Train Isolation Forest on normal traffic only
    iso = train_isolation_forest(X_train_bal, y_train_bal, le)

    # Module 6: Evaluate on REAL unseen test set
    metrics = evaluate_model(rf, X_test, y_test, le, RESULTS_PATH)

    # Module 7: Save models
    save_models(rf, iso, MODEL_PATH)

    log.info("\n" + "=" * 60)
    log.info("  TRAINING COMPLETE")
    log.info(f"  Accuracy : {metrics['accuracy'] * 100:.2f}%")
    log.info(f"  F1-Score : {metrics['f1']       * 100:.2f}%")
    log.info("=" * 60)

    return rf, iso, le, metrics


if __name__ == '__main__':
    run_training()
