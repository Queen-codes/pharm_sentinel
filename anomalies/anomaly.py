from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict
import math
import uuid


ANOMALY_TYPES = [
    "RAPID_TURNOVER",
    "IMPOSSIBLE_QUANTITY",
    "GEOGRAPHIC_IMPOSSIBILITY",
    "GHOST_STOCK",
]

DEFAULT_THRESHOLDS = {
    "RAPID_TURNOVER_HOURS": 24,
    "RAPID_TURNOVER_MULTIPLIER": 2.5,
    "IMPOSSIBLE_QUANTITY_MULTIPLIER": 10,
    "GEOGRAPHIC_IMPOSSIBLE_KM": 300,
    "GEOGRAPHIC_IMPOSSIBLE_HOURS": 6,
}


def create_anomaly(
    *,
    anomaly_type: str,
    severity: str,
    facility_id: str | None,
    med_id: str | None,
    timestamp: datetime,
    details: str,
    batch_id: str | None = None,
    evidence: Dict | None = None,
) -> Dict:
    return {
        "anomaly_id": f"ANOM_{uuid.uuid4().hex[:10].upper()}",
        "anomaly_type": anomaly_type,
        "severity": severity,
        "facility_id": facility_id,
        "med_id": med_id,
        "batch_id": batch_id,
        "timestamp": timestamp.isoformat(),
        "details": details,
        "evidence": evidence or {},
        "source": "SIMULATION",
        "is_active": True,
    }


# harversine function to calcuate distance between two locations
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def detect_rapid_turnover(
    movements: List[Dict],
    events: List[Dict],
    current_time: datetime,
    thresholds=DEFAULT_THRESHOLDS,
) -> List[Dict]:
    anomalies = []

    # calculate how far back to detect movements of rapid turnover < 24hrs
    period_since = current_time - timedelta(hours=thresholds["RAPID_TURNOVER_HOURS"])

    # total dispensed per facility and medication
    dispensed = defaultdict(int)

    for mov in movements:
        if mov["movement_type"] != "DISPENSE":
            continue
        # convert movement's timestamp string back to datetime obj for easier comparison
        ts = datetime.fromisoformat(mov["timestamp"])
        if ts < period_since:
            continue

        # count how much was dispensed per fac-med tuple pair
        key = (mov["facility_id"], mov["med_id"])
        dispensed[key] += abs(mov["quantity_change"])

    expected_qty = defaultdict(int)
    for event in events:
        if event["event_type"] in ("LOW_STOCK", "CRITICAL_STOCK"):
            key = (event["facility_id"], event["med_id"])
            expected_qty[key] += event["data"].get("reorder_point", 0)

    for key, quantity in dispensed.items():
        baseline = expected_qty.get(key)
        if not baseline:
            continue

        if quantity > baseline * thresholds["RAPID_TURNOVER_MULTIPLIER"]:
            anomalies.append(
                create_anomaly(
                    anomaly_type="RAPID_TURNOVER",
                    severity="HIGH",
                    facility_id=key[0],
                    med_id=key[1],
                    timestamp=current_time,
                    details=f"Dispensed {quantity} units in short window, expected ~{baseline}",
                    evidence={
                        "dispensed": quantity,
                        "expected": baseline,
                    },
                )
            )

    return anomalies


def detect_impossible_quantity(
    movements: List[Dict],
    inventory: List[Dict],
    batches: List[Dict],
    current_time: datetime,
    thresholds=DEFAULT_THRESHOLDS,
) -> List[Dict]:
    anomalies = []

    """initial_by_batch = {
        inv["batch_id"]: inv.get("initial_quantity", None) for inv in inventory
    }"""

    # get initial quantity of a batch
    initial_qty_by_batch = {b["batch_id"]: b["initial_quantity"] for b in batches}

    dispensed_by_batch = defaultdict(int)
    # get the amount dispensed already per batch
    for mov in movements:
        if mov["movement_type"] == "DISPENSE":
            dispensed_by_batch[mov["batch_id"]] += abs(mov["quantity_change"])

    for batch_id, dispensed in dispensed_by_batch.items():
        initial = initial_qty_by_batch.get(batch_id)
        if not initial:
            continue

        if dispensed > initial * thresholds["IMPOSSIBLE_QUANTITY_MULTIPLIER"]:
            anomalies.append(
                create_anomaly(
                    anomaly_type="IMPOSSIBLE_QUANTITY",
                    severity="CRITICAL",
                    facility_id=None,
                    med_id=None,
                    batch_id=batch_id,
                    timestamp=current_time,
                    details=f"Dispensed {dispensed} units but initial was {initial}",
                    evidence={
                        "initial_quantity": initial,
                        "dispensed_quantity": dispensed,
                    },
                )
            )

    return anomalies


def detect_geographic_impossibility(
    movements: List[Dict],
    facilities: List[Dict],
    current_time: datetime,
    thresholds=DEFAULT_THRESHOLDS,
) -> List[Dict]:
    anomalies = []

    facility_lookup = {f["facility_id"]: f for f in facilities}
    movements_by_batch = defaultdict(list)

    for mov in movements:
        movements_by_batch[mov["batch_id"]].append(mov)

    for batch_id, batch_moves in movements_by_batch.items():
        # sort batch movements with time
        batch_moves.sort(key=lambda movement: movement["timestamp"])

        for i in range(len(batch_moves) - 1):
            former_movement = batch_moves[i]
            latter_movement = batch_moves[i + 1]

            former_fac = facility_lookup.get(former_movement["facility_id"])
            latter_fac = facility_lookup.get(latter_movement["facility_id"])

            if not former_fac or not latter_fac:
                continue

            former_time = datetime.fromisoformat(former_movement["timestamp"])
            latter_time = datetime.fromisoformat(latter_movement["timestamp"])
            hours_between = abs((latter_time - former_time).total_seconds()) / 3600

            distance_in_km = haversine_km(
                former_fac["latitude"],
                former_fac["longitude"],
                latter_fac["latitude"],
                latter_fac["longitude"],
            )

            if (
                distance_in_km > thresholds["GEOGRAPHIC_IMPOSSIBLE_KM"]
                and hours_between < thresholds["GEOGRAPHIC_IMPOSSIBLE_HOURS"]
            ):
                anomalies.append(
                    create_anomaly(
                        anomaly_type="GEOGRAPHIC_IMPOSSIBILITY",
                        severity="CRITICAL",
                        facility_id=None,
                        med_id=former_movement["med_id"],
                        batch_id=batch_id,
                        timestamp=current_time,
                        details=f"Batch appeared at two distant locations ({round(distance_in_km, 1)} km apart) within {round(hours_between, 2)} hours",
                        evidence={
                            "first_facility": former_fac["facility_id"],
                            "second_facility": latter_fac["facility_id"],
                            "distance_km": round(distance_in_km, 1),
                            "hours_between": round(hours_between, 2),
                        },
                    )
                )

    return anomalies


def detect_ghost_stock(
    inventory: List[Dict],
    movements: List[Dict],
    current_time: datetime,
) -> List[Dict]:
    anomalies = []

    received_batches = {
        mov["batch_id"]
        for mov in movements
        if mov["movement_type"] in ("RESTOCK", "TRANSFER_IN")
    }

    for inv in inventory:
        if inv["quantity"] > 0 and inv["batch_id"] not in received_batches:
            anomalies.append(
                create_anomaly(
                    anomaly_type="GHOST_STOCK",
                    severity="HIGH",
                    facility_id=inv["facility_id"],
                    med_id=inv["med_id"],
                    batch_id=inv["batch_id"],
                    timestamp=current_time,
                    details="Inventory exists without any receipt movement",
                )
            )

    return anomalies


def generate_anomalies(
    *,
    inventory: List[Dict],
    movements: List[Dict],
    events: List[Dict],
    facilities: List[Dict],
    batches: List[Dict],
    current_time: datetime,
    thresholds=DEFAULT_THRESHOLDS,
) -> List[Dict]:

    anomalies = []

    anomalies.extend(detect_rapid_turnover(movements, events, current_time, thresholds))
    anomalies.extend(
        detect_impossible_quantity(
            movements, inventory, batches, current_time, thresholds
        )
    )
    anomalies.extend(
        detect_geographic_impossibility(movements, facilities, current_time, thresholds)
    )
    anomalies.extend(detect_ghost_stock(inventory, movements, current_time))

    return anomalies
