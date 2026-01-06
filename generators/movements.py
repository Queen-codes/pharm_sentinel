import random
from datetime import datetime, timedelta
from collections import defaultdict


def dispense(inventory, quantity, timestamp):
    """
    for recording that medicine was dispensed from a batch simulating real-life dispense.
    """
    return _record_movement(
        inventory=inventory,
        movement_type="DISPENSE",
        quantity_change=-abs(quantity),
        timestamp=timestamp,
        reference_id=f"DIS_{random.randint(10000, 999999)}",
    )


def restock(inventory, quantity, timestamp):
    """
    for recording restock batch
    """
    return _record_movement(
        inventory=inventory,
        movement_type="RESTOCK",
        quantity_change=abs(quantity),
        timestamp=timestamp,
        reference_id=f"RES_{random.randint(10000, 999999)}",
    )


def transfer_out(inventory, quantity, timestamp, destination_facility_id):
    """
    for meds that leave a facility when a transfer request is fuffilled
    """
    return _record_movement(
        inventory=inventory,
        movement_type="TRANSFER_OUT",
        quantity_change=-abs(quantity),  # has to be a negative value
        timestamp=timestamp,
        reference_id=f"TRF_TO_{destination_facility_id}",
    )


def transfer_in(inventory, quantity, timestamp, source_facility_id):
    """
    Record stock arriving at a facility.
    """
    return _record_movement(
        inventory=inventory,
        movement_type="TRANSFER_IN",
        quantity_change=abs(quantity),
        timestamp=timestamp,
        reference_id=f"TRF_FROM_{source_facility_id}",
    )


def expiry_withdraw(inventory, quantity, timestamp):
    """
    to track stock that was removed from shelf due to expiry
    """
    safe_quantity = min(abs(quantity), inventory["quantity"])
    return _record_movement(
        inventory=inventory,
        movement_type="EXPIRY_WITHDRAW",
        quantity_change=-safe_quantity,
        timestamp=timestamp,
        reference_id="EXPIRY_AUDIT",
    )


def _record_movement(
    inventory, movement_type, quantity_change, timestamp, reference_id
):
    """
    function that:
    - updates inventory quantity
    - returns a movement record
    """

    if isinstance(timestamp, datetime):
        timestamp = timestamp.isoformat()

    previous_quantity = inventory["quantity"]
    new_quantity = max(0, previous_quantity + quantity_change)

    movement = {
        "movement_id": f"MOV_{random.randint(100000, 999999)}",
        "inventory_id": inventory["inventory_id"],
        "facility_id": inventory["facility_id"],
        "batch_id": inventory["batch_id"],
        "med_id": inventory["med_id"],
        "movement_type": movement_type,
        "quantity_change": quantity_change,
        "quantity_after": new_quantity,
        "timestamp": timestamp,
        "reference_id": reference_id,
        "source": "HISTORICAL_SEED",
    }

    inventory["quantity"] = new_quantity
    return movement


def seed_historical_movements(inventory, medications, start_date, days=30, seed=42):

    random.seed(seed)
    movements = []

    med_lookup = {m["med_id"]: m for m in medications}
    inventory_by_med = defaultdict(list)

    for inv in inventory:
        inventory_by_med[inv["med_id"]].append(inv)

    for day in range(days):
        day_time = start_date + timedelta(days=day)

        for med_id, batches in inventory_by_med.items():
            daily_demand = med_lookup[med_id]["base_demand"] / 30

            for batch in batches:
                if batch["quantity"] <= 0:
                    continue

                if random.random() < 0.8:
                    qty = max(1, int(random.gauss(daily_demand, daily_demand * 0.35)))
                    qty = min(qty, batch["quantity"])

                    movements.append(
                        dispense(batch, qty, day_time + timedelta(hours=12))
                    )

    return movements


if __name__ == "__main__":

    from inventory import generate_inventory
    from companies import generate_companies
    from brands import generate_brands
    from batches import generate_batches
    from facilities import generate_facilities
    from medications import generate_medications

    meds = generate_medications()
    brands = generate_brands(meds)
    companies = generate_companies()
    batches = generate_batches(brands, companies)
    facilities = generate_facilities()
    inventory = generate_inventory(facilities, batches, meds)

    start_date = datetime(2025, 11, 12)
    movement = seed_historical_movements(inventory, meds, start_date)
    # print(movement[0])

{
    "movement_id": "MOV_246316",
    "inventory_id": "INV_00001",
    "facility_id": "FAC_001",
    "batch_id": "BAT_0008",
    "med_id": "MED_001",
    "movement_type": "DISPENSE",
    "quantity_change": -8,
    "quantity_after": 399,
    "timestamp": "2025-11-12T12:00:00",
    "reference_id": "DIS_244053",
    "source": "HISTORICAL_SEED",
}
