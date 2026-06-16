"""
predict.py
NIDS + ML + Blockchain Project — BTech
Real-time packet capture, feature extraction and detection pipeline

PIPELINE:
  Scapy captures packets
      ↓
  Flow aggregation (group packets into flows)
      ↓
  Feature extraction (78 features matching training data)
"""


import json
import os
import time
import queue
import joblib
import warnings
import numpy as np
import pandas as pd
from datetime import datetime
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from scapy.all import sniff, IP, TCP, UDP, ICMP

from logger import logger

warnings.filterwarnings('ignore')

# ─────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────

MODEL_PATH      = 'models/'
RF_MODEL        = 'random_forest.pkl'
ISO_MODEL       = 'isolation_forest.pkl'
ENCODER         = 'label_encoder.pkl'

NETWORK_IFACE   = None          # None = default interface, or set e.g. 'eth0'
FLOW_TIMEOUT    = 30            # seconds before an idle flow is considered complete
ALERT_CALLBACK  = None          # set externally to hook into blockchain logger
FEATURES_FILE   = 'features_cicids.json'

# Confidence threshold — below this, flag as uncertain
CONFIDENCE_THRESHOLD = 0.6

# Isolation Forest threshold — scores below this flagged as anomaly
ISOLATION_THRESHOLD  = -0.1

# Attack severity mapping
SEVERITY = {
    'Normal'     : 'INFO',
    'PortScan'   : 'MEDIUM',
    'BruteForce' : 'HIGH',
    'DoS'        : 'CRITICAL',
    'Anomaly'    : 'HIGH',
}

# ─────────────────────────────────────────────────────────────
# MODULE 1 — Load models
# ─────────────────────────────────────────────────────────────

def load_models(model_path):
    """Load trained Random Forest, Isolation Forest and label encoder."""
    logger.info("Loading models...")

    import os
    rf  = joblib.load(os.path.join(model_path, RF_MODEL))
    iso = joblib.load(os.path.join(model_path, ISO_MODEL))
    le  = joblib.load(os.path.join(model_path, ENCODER))

    logger.info(f"Random Forest    : loaded ({rf.n_estimators} trees)")
    logger.info(f"Isolation Forest : loaded")
    logger.info(f"Label classes    : {list(le.classes_)}")

    return rf, iso, le

# ─────────────────────────────────────────────────────────────
# MODULE 2 — Flow tracker
# ─────────────────────────────────────────────────────────────

class FlowTracker:
    """
    Aggregates individual packets into network flows.
    A flow = all packets sharing the same 5-tuple:
    (src_ip, dst_ip, src_port, dst_port, protocol)
    """

    def __init__(self, timeout=FLOW_TIMEOUT):
        self.flows   = defaultdict(list)
        self.timeout = timeout

    def get_flow_key(self, packet):
        """Extract 5-tuple flow key from packet."""
        if IP not in packet:
            return None

        src_ip   = packet[IP].src
        dst_ip   = packet[IP].dst
        protocol = packet[IP].proto

        src_port = dst_port = 0
        if TCP in packet:
            src_port = packet[TCP].sport
            dst_port = packet[TCP].dport
        elif UDP in packet:
            src_port = packet[UDP].sport
            dst_port = packet[UDP].dport

        return (src_ip, dst_ip, src_port, dst_port, protocol)

    def add_packet(self, packet):
        """Add packet to its flow. Returns completed flow if timeout reached."""
        try:
            key = self.get_flow_key(packet)
            if key is None:
                return None, None
        except Exception:
            return None, None

        self.flows[key].append({
            'packet'    : packet,
            'timestamp' : time.time(),
            'size'      : len(packet),
        })

        if TCP in packet and ((packet[TCP].flags & 0x01) or (packet[TCP].flags & 0x04)):
            completed = self.flows.pop(key)
            return key, completed

        # Check if flow is complete (timeout)
        flow_packets = self.flows[key]
        if len(flow_packets) > 1:
            duration = flow_packets[-1]['timestamp'] - flow_packets[0]['timestamp']
            if duration >= self.timeout and len(flow_packets) >= 2:
                completed = self.flows.pop(key)
                return key, completed

        return None, None

    def flush_stale_flows(self):
        """Force-complete flows that have been idle too long."""
        now     = time.time()
        stale   = []
        results = []

        for key, packets in self.flows.items():
            if packets and (now - packets[-1]['timestamp']) > self.timeout:
                stale.append(key)

        for key in stale:
            if len(self.flows[key]) >= 2:
                results.append((key, self.flows.pop(key)))
            else:
                self.flows.pop(key)

        return results

# ─────────────────────────────────────────────────────────────
# MODULE 3 — Feature extraction
# ─────────────────────────────────────────────────────────────

def extract_features(flow_key, flow_packets):
    """
    Extract the 78 features matching CICIDS2017 training data.
    Computes statistical features from raw flow packets.
    """
    src_ip, dst_ip, src_port, dst_port, protocol = flow_key

    packets    = [p['packet'] for p in flow_packets]
    timestamps = [p['timestamp'] for p in flow_packets]
    sizes      = [p['size'] for p in flow_packets]

    # Split into forward (client→server) and backward (server→client)
    fwd = [p for p in flow_packets if p['packet'][IP].src == src_ip]
    bwd = [p for p in flow_packets if p['packet'][IP].src != src_ip]

    fwd_sizes  = [p['size'] for p in fwd] or [0]
    bwd_sizes  = [p['size'] for p in bwd] or [0]
    fwd_times  = [p['timestamp'] for p in fwd] or [0]
    bwd_times  = [p['timestamp'] for p in bwd] or [0]

    duration = max(timestamps) - min(timestamps) if len(timestamps) > 1 else 0.000001

    # Inter-arrival times
    all_iats = np.diff(sorted(timestamps)).tolist() or [0]
    fwd_iats = np.diff(sorted(fwd_times)).tolist()  or [0]
    bwd_iats = np.diff(sorted(bwd_times)).tolist()  or [0]

    # TCP flags
    fin = syn = rst = psh = ack = urg = cwe = ece = 0
    for p in packets:
        if TCP in p:
            flags = p[TCP].flags
            fin  += 1 if flags & 0x01 else 0
            syn  += 1 if flags & 0x02 else 0
            rst  += 1 if flags & 0x04 else 0
            psh  += 1 if flags & 0x08 else 0
            ack  += 1 if flags & 0x10 else 0
            urg  += 1 if flags & 0x20 else 0
            cwe  += 1 if flags & 0x40 else 0
            ece  += 1 if flags & 0x80 else 0

    # Init window bytes
    init_win_fwd = packets[0][TCP].window  if packets and TCP in packets[0]  else 0
    init_win_bwd = packets[-1][TCP].window if packets and TCP in packets[-1] else 0

    total_fwd_bytes = sum(fwd_sizes)
    total_bwd_bytes = sum(bwd_sizes)
    total_bytes     = total_fwd_bytes + total_bwd_bytes

    features = {
        'Destination Port'            : dst_port,
        'Flow Duration'               : int(duration * 1e6),
        'Total Fwd Packets'           : len(fwd),
        'Total Backward Packets'      : len(bwd),
        'Total Length of Fwd Packets' : total_fwd_bytes,
        'Total Length of Bwd Packets' : total_bwd_bytes,
        'Fwd Packet Length Max'       : max(fwd_sizes),
        'Fwd Packet Length Min'       : min(fwd_sizes),
        'Fwd Packet Length Mean'      : np.mean(fwd_sizes),
        'Fwd Packet Length Std'       : np.std(fwd_sizes),
        'Bwd Packet Length Max'       : max(bwd_sizes),
        'Bwd Packet Length Min'       : min(bwd_sizes),
        'Bwd Packet Length Mean'      : np.mean(bwd_sizes),
        'Bwd Packet Length Std'       : np.std(bwd_sizes),
        'Flow Bytes/s'                : total_bytes / duration,
        'Flow Packets/s'              : len(packets) / duration,
        'Flow IAT Mean'               : np.mean(all_iats),
        'Flow IAT Std'                : np.std(all_iats),
        'Flow IAT Max'                : max(all_iats),
        'Flow IAT Min'                : min(all_iats),
        'Fwd IAT Total'               : sum(fwd_iats),
        'Fwd IAT Mean'                : np.mean(fwd_iats),
        'Fwd IAT Std'                 : np.std(fwd_iats),
        'Fwd IAT Max'                 : max(fwd_iats),
        'Fwd IAT Min'                 : min(fwd_iats),
        'Bwd IAT Total'               : sum(bwd_iats),
        'Bwd IAT Mean'                : np.mean(bwd_iats),
        'Bwd IAT Std'                 : np.std(bwd_iats),
        'Bwd IAT Max'                 : max(bwd_iats),
        'Bwd IAT Min'                 : min(bwd_iats),
        'Fwd PSH Flags'               : psh,
        'Bwd PSH Flags'               : 0,
        'Fwd URG Flags'               : urg,
        'Bwd URG Flags'               : 0,
        'Fwd Header Length'           : len(fwd) * 20,
        'Bwd Header Length'           : len(bwd) * 20,
        'Fwd Packets/s'               : len(fwd) / duration,
        'Bwd Packets/s'               : len(bwd) / duration,
        'Min Packet Length'           : min(sizes),
        'Max Packet Length'           : max(sizes),
        'Packet Length Mean'          : np.mean(sizes),
        'Packet Length Std'           : np.std(sizes),
        'Packet Length Variance'      : np.var(sizes),
        'FIN Flag Count'              : fin,
        'SYN Flag Count'              : syn,
        'RST Flag Count'              : rst,
        'PSH Flag Count'              : psh,
        'ACK Flag Count'              : ack,
        'URG Flag Count'              : urg,
        'CWE Flag Count'              : cwe,
        'ECE Flag Count'              : ece,
        'Down/Up Ratio'               : len(bwd) / max(len(fwd), 1),
        'Average Packet Size'         : np.mean(sizes),
        'Avg Fwd Segment Size'        : np.mean(fwd_sizes),
        'Avg Bwd Segment Size'        : np.mean(bwd_sizes),
        'Fwd Header Length.1'         : len(fwd) * 20,
        'Fwd Avg Bytes/Bulk'          : 0,
        'Fwd Avg Packets/Bulk'        : 0,
        'Fwd Avg Bulk Rate'           : 0,
        'Bwd Avg Bytes/Bulk'          : 0,
        'Bwd Avg Packets/Bulk'        : 0,
        'Bwd Avg Bulk Rate'           : 0,
        'Subflow Fwd Packets'         : len(fwd),
        'Subflow Fwd Bytes'           : total_fwd_bytes,
        'Subflow Bwd Packets'         : len(bwd),
        'Subflow Bwd Bytes'           : total_bwd_bytes,
        'Init_Win_bytes_forward'      : init_win_fwd,
        'Init_Win_bytes_backward'     : init_win_bwd,
        'act_data_pkt_fwd'            : len(fwd),
        'min_seg_size_forward'        : min(fwd_sizes),
        'Active Mean'                 : np.mean(all_iats),
        'Active Std'                  : np.std(all_iats),
        'Active Max'                  : max(all_iats),
        'Active Min'                  : min(all_iats),
        'Idle Mean'                   : np.mean(all_iats),
        'Idle Std'                    : np.std(all_iats),
        'Idle Max'                    : max(all_iats),
        'Idle Min'                    : min(all_iats),
    }

    features_df = pd.DataFrame([features])
    feature_path = os.path.join(MODEL_PATH, FEATURES_FILE)
    if os.path.exists(feature_path):
        try:
            with open(feature_path, "r", encoding="utf-8") as fh:
                expected_features = json.load(fh)
            features_df = features_df.reindex(columns=expected_features, fill_value=0)
        except Exception:
            pass

    return features_df

# ─────────────────────────────────────────────────────────────
# MODULE 4 — Detection engine
# ─────────────────────────────────────────────────────────────

def detect(flow_key, flow_packets, rf, iso, le):
    """
    Run extracted features through both models.
    Returns structured alert dict.
    """
    src_ip, dst_ip, src_port, dst_port, protocol = flow_key

    try:
        features_df = extract_features(flow_key, flow_packets)

        # Replace any inf/nan from edge case flows
        features_df.replace([np.inf, -np.inf], 0, inplace=True)
        features_df.fillna(0, inplace=True)

        # ── Random Forest prediction ──
        rf_pred        = rf.predict(features_df)[0]
        rf_proba       = rf.predict_proba(features_df)[0]
        rf_confidence  = rf_proba.max()
        rf_label       = le.classes_[rf_pred]

        # ── Isolation Forest anomaly score ──
        iso_score      = iso.decision_function(features_df)[0]
        iso_anomaly    = iso_score < ISOLATION_THRESHOLD

        # ── Final classification decision ──
        if rf_label == 'Normal' and iso_anomaly:
            final_label = 'Anomaly'
            note        = f'RF:Normal but IsoForest score={iso_score:.3f}'
        elif rf_confidence < CONFIDENCE_THRESHOLD:
            final_label = 'Anomaly'
            note        = f'RF low confidence={rf_confidence:.2f}'
        else:
            final_label = rf_label
            note        = f'RF confidence={rf_confidence:.2f}'

        alert = {
            'timestamp'      : datetime.utcnow().isoformat(),
            'src_ip'         : src_ip,
            'dst_ip'         : dst_ip,
            'src_port'       : src_port,
            'dst_port'       : dst_port,
            'protocol'       : protocol,
            'label'          : final_label,
            'severity'       : SEVERITY.get(final_label, 'UNKNOWN'),
            'rf_label'       : rf_label,
            'rf_confidence'  : round(float(rf_confidence), 4),
            'iso_score'      : round(float(iso_score), 4),
            'packet_count'   : len(flow_packets),
            'note'           : note,
            'is_attack'      : final_label != 'Normal',
        }

        return alert

    except Exception as e:
        return {
            'timestamp'  : datetime.utcnow().isoformat(),
            'src_ip'     : src_ip,
            'error'      : str(e),
            'is_attack'  : False,
        }

# ─────────────────────────────────────────────────────────────
# MODULE 5 — Alert handler
# ─────────────────────────────────────────────────────────────

def handle_alert(alert, alert_callback=None):
    """
    Log alert.
    If alert_callback is set, pass alert to blockchain logger.
    """
    if not alert.get('is_attack'):
        return

    severity = alert.get('severity', 'INFO')
    label    = alert.get('label', 'Unknown')
    src_ip   = alert.get('src_ip', '?')
    dst_ip   = alert.get('dst_ip', '?')
    conf     = alert.get('rf_confidence', 0)
    ts       = alert.get('timestamp', '')

    alert_msg = (
        f"[ALERT] {ts} | "
        f"Type: {label} ({severity}) | "
        f"From: {src_ip}:{alert.get('src_port')} -> {dst_ip}:{alert.get('dst_port')} | "
        f"Packets: {alert.get('packet_count')} | "
        f"RF Conf: {conf:.2%} | "
        f"Note: {alert.get('note')}"
    )
    logger.warning(alert_msg)

    # Pass to blockchain logger if connected
    if alert_callback:
        try:
            alert_callback(alert)
        except Exception as e:
            logger.error(f"Blockchain logging failed: {e}")

# ─────────────────────────────────────────────────────────────
# MODULE 6 — Live capture loop
# ─────────────────────────────────────────────────────────────

def start_live_capture(rf, iso, le, iface=NETWORK_IFACE, alert_callback=None):
    """
    Start live packet capture using Scapy.
    Processes packets into flows and runs detection.
    """
    logger.info("Starting live capture...")
    logger.info(f"Interface : {iface or 'default'}")

    tracker       = FlowTracker(timeout=FLOW_TIMEOUT)
    alerts_total  = 0
    packets_total = 0

    flow_queue = queue.Queue(maxsize=2000)

    def inference_worker():
        nonlocal alerts_total
        while True:
            item = flow_queue.get()
            if item is None:
                break
            k, flow = item
            alert = detect(k, flow, rf, iso, le)
            handle_alert(alert, alert_callback)
            if alert.get('is_attack'):
                alerts_total += 1
            flow_queue.task_done()

    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(inference_worker)

    def process_packet(packet):
        nonlocal packets_total

        if IP not in packet:
            return

        packets_total += 1

        # Add to flow tracker
        key, completed_flow = tracker.add_packet(packet)

        if completed_flow:
            try:
                flow_queue.put_nowait((key, completed_flow))
            except queue.Full:
                logger.warning("Flow queue full, dropping flow!")

        # Periodically flush stale flows
        if packets_total % 100 == 0:
            stale_flows = tracker.flush_stale_flows()
            for k, flow in stale_flows:
                try:
                    flow_queue.put_nowait((k, flow))
                except queue.Full:
                    logger.warning("Flow queue full, dropping flow!")

    try:
        sniff(
            iface  = iface,
            filter = "ip",
            prn    = process_packet,
            store  = False
        )
    except KeyboardInterrupt:
        logger.info("Capture stopped.")
        logger.info(f"Total packets : {packets_total}")
        logger.info(f"Total alerts  : {alerts_total}")
    finally:
        flow_queue.put(None)
        executor.shutdown(wait=True)

# ─────────────────────────────────────────────────────────────
# MODULE 7 — File-based prediction (for testing with datasets)
# ─────────────────────────────────────────────────────────────

def predict_from_file(filepath, rf, iso, le, sample_size=1000):
    """
    Run prediction on a CSV file (for GNS3 testing without live capture).
    Useful for validating the predict pipeline against known labels.
    """
    logger.info(f"Predicting from file: {filepath}")

    df = pd.read_csv(filepath)
    df.columns = df.columns.str.strip()

    if 'Label' in df.columns:
        true_labels = df['Label'].copy()
        df = df.drop('Label', axis=1)
    else:
        true_labels = None

    # Sample for quick testing
    if sample_size and len(df) > sample_size:
        df = df.sample(sample_size, random_state=42)
        if true_labels is not None:
            true_labels = true_labels.loc[df.index]

    df.replace([np.inf, -np.inf], 0, inplace=True)
    df.fillna(0, inplace=True)

    rf_preds       = rf.predict(df)
    rf_probas      = rf.predict_proba(df).max(axis=1)
    iso_scores     = iso.decision_function(df)
    predicted_labels = le.inverse_transform(rf_preds)

    results = pd.DataFrame({
        'Predicted'      : predicted_labels,
        'RF_Confidence'  : rf_probas.round(4),
        'ISO_Score'      : iso_scores.round(4),
        'Is_Attack'      : predicted_labels != 'Normal',
    })

    if true_labels is not None:
        results['True_Label'] = true_labels.values

    logger.info("Prediction summary:\n" + results['Predicted'].value_counts().to_string())
    logger.info("Sample results:\n" + results.head(10).to_string())

    return results

# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys

    rf, iso, le = load_models(MODEL_PATH)

    if len(sys.argv) > 1 and sys.argv[1] == '--file':
        # Test mode: predict from CSV file
        # Usage: python predict.py --file path/to/file.csv
        filepath = sys.argv[2] if len(sys.argv) > 2 else 'data/raw/cicids2017/Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv'
        results = predict_from_file(filepath, rf, iso, le)
    else:
        # Live mode: capture from network interface
        logger.info("NIDS LIVE DETECTION - STARTING")
        start_live_capture(rf, iso, le, alert_callback=ALERT_CALLBACK)
