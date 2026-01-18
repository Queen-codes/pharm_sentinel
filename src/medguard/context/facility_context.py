"""
This file/module is for one specific facility view only(preferablly logged in).
The purpose is to seperate each facility's data in the system so it never shows other facilities.
"""

from datetime import datetime, timedelta
from typing import Dict
from medguard.db.database import get_connection_to_db


def get_facility_context(facility_id: str) -> Dict:
    """
    Returns context for a facility.

    Args:
        facility_id:

    #TODO: TEST, design web interface based on this for each facility
    Intended Output shape:
    {
        "facility_id": "FAC_001",
        "facility_name": "Lagos General Hospital",
        "inventory": {
            "total_items": int,
            "low_stock": [...],
            "stockouts": [...],
            "expiring_soon": [...]
        },
        "alerts": {
            "reorder_suggestions": [...] # notifications that'll come in
        },
        "transfers": {
            "pending_incoming": [...],  # transfers to the specific facility being viewed atm
            "pending_outgoing": [...],  # transfers from this facility that other fac/llm are awaiting their approval
            "recent_completed": [...]
        }
    }
    """
    if not facility_id:
        raise ValueError("facility_id is required")

    conn = get_connection_to_db()
    cursor = conn.cursor()

    # get facility info
    cursor.execute(
        "SELECT name, city, tier FROM facilities WHERE facility_id = ?", (facility_id,)
    )
    fac_row = cursor.fetchone()
    facility_name = fac_row["name"] if fac_row else "Unknown"

    snapshot = {
        "facility_id": facility_id,
        "facility_name": facility_name,
        "inventory": _get_facility_inventory(cursor, facility_id),
        "transfers": _get_facility_transfers(cursor, facility_id),
        "alerts": _get_facility_alerts(cursor, facility_id),
    }

    conn.close()
    return snapshot


def _get_facility_inventory(cursor, facility_id: str) -> Dict:
    """Get inventory status for this facility."""

    # Stockouts
    cursor.execute(
        """
        SELECT
            m.med_id,
            m.generic_name as medication_name,
            m.category,
            MIN(i.reorder_point) as reorder_point
        FROM inventory i
        JOIN batches b ON i.batch_id = b.batch_id
        JOIN brands br ON b.brand_id = br.brand_id
        JOIN medications m ON br.med_id = m.med_id
        WHERE i.facility_id = ?
        GROUP BY m.med_id
        HAVING SUM(i.quantity) = 0
    """,
        (facility_id,),
    )
    stockouts = [dict(row) for row in cursor.fetchall()]

    # Low stock
    cursor.execute(
        """
        SELECT
            m.med_id,
            m.generic_name as medication_name,
            m.category,
            m.base_demand,
            SUM(i.quantity) as total_quantity,
            MIN(i.reorder_point) as reorder_point,
            CAST(SUM(i.quantity) AS FLOAT) / NULLIF(m.base_demand, 0) as days_remaining
        FROM inventory i
        JOIN batches b ON i.batch_id = b.batch_id
        JOIN brands br ON b.brand_id = br.brand_id
        JOIN medications m ON br.med_id = m.med_id
        WHERE i.facility_id = ?
        GROUP BY m.med_id
        HAVING SUM(i.quantity) > 0 AND SUM(i.quantity) <= MIN(i.reorder_point)
        ORDER BY days_remaining ASC
    """,
        (facility_id,),
    )
    low_stock = [dict(row) for row in cursor.fetchall()]

    # expiring soon threshold of 14 days. increase/decrease??
    expiry_threshold = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
    cursor.execute(
        """
        SELECT
            i.batch_id,
            b.batch_number,
            b.expiry_date,
            br.brand_name,
            m.generic_name as medication_name,
            i.quantity,
            CAST(julianday(b.expiry_date) - julianday('now') AS INTEGER) as days_to_expiry
        FROM inventory i
        JOIN batches b ON i.batch_id = b.batch_id
        JOIN brands br ON b.brand_id = br.brand_id
        JOIN medications m ON br.med_id = m.med_id
        WHERE i.facility_id = ?
            AND i.quantity > 0
            AND b.expiry_date <= ?
            AND b.expiry_date > date('now')
        ORDER BY days_to_expiry ASC
    """,
        (facility_id, expiry_threshold),
    )
    expiring_soon = [dict(row) for row in cursor.fetchall()]

    # Total items count
    cursor.execute(
        "SELECT COUNT(*) as count FROM inventory WHERE facility_id = ? AND quantity > 0",
        (facility_id,),
    )
    total_items = cursor.fetchone()["count"]

    return {
        "total_items": total_items,
        "stockouts": stockouts,
        "low_stock": low_stock,
        "expiring_soon": expiring_soon,
    }


def _get_facility_transfers(cursor, facility_id: str) -> Dict:
    """Get transfers involving this facility."""
    # Request flow: Request fac requests -> Pending -> Sender approves -> Completed.

    cursor.execute(
        """
        SELECT
            t.transfer_id,
            f.name as from_facility_name,
            m.generic_name as medication_name,
            t.quantity,
            t.created_at,
            t.status
        FROM transfers t
        JOIN facilities f ON t.from_facility_id = f.facility_id
        JOIN medications m ON t.medication_id = m.med_id
        WHERE t.to_facility_id = ? AND t.status = 'PENDING'
    """,
        (facility_id,),
    )
    pending_incoming = [dict(row) for row in cursor.fetchall()]

    # Pending OUTGOING (Me -> Others) who are waiting for my approval from my own fac
    cursor.execute(
        """
        SELECT
            t.transfer_id,
            f.name as to_facility_name,
            m.generic_name as medication_name,
            t.quantity,
            t.created_at,
            t.status,
            t.transfer_reason
        FROM transfers t
        JOIN facilities f ON t.to_facility_id = f.facility_id
        JOIN medications m ON t.medication_id = m.med_id
        WHERE t.from_facility_id = ? AND t.status = 'PENDING'
    """,
        (facility_id,),
    )
    pending_outgoing = [dict(row) for row in cursor.fetchall()]

    # recently completed transfers :last 7 days for both sending and receiving:
    # TODO: MAYBE DESIGN SEPERATE TABS FOR BOTH/OR A WAY TO FILTER ON THE WEB APP -> ALL TRANSFERS - SENT - RECEIVED
    seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
    cursor.execute(
        """
        SELECT
            t.transfer_id,
            CASE 
                WHEN t.from_facility_id = ? THEN 'OUTGOING'
                ELSE 'INCOMING'
            END as direction,
            CASE 
                WHEN t.from_facility_id = ? THEN f2.name
                ELSE f1.name
            END as other_facility_name,
            m.generic_name as medication_name,
            t.quantity,
            t.completed_at
        FROM transfers t
        JOIN facilities f1 ON t.from_facility_id = f1.facility_id
        JOIN facilities f2 ON t.to_facility_id = f2.facility_id
        JOIN medications m ON t.medication_id = m.med_id
        WHERE (t.from_facility_id = ? OR t.to_facility_id = ?)
            AND t.status = 'COMPLETED'
            AND t.completed_at >= ?
        ORDER BY t.completed_at DESC
    """,
        (facility_id, facility_id, facility_id, facility_id, seven_days_ago),
    )
    recent_completed = [dict(row) for row in cursor.fetchall()]

    return {
        "pending_incoming": pending_incoming,
        "pending_outgoing": pending_outgoing,
        "recent_completed": recent_completed,
    }


def _get_facility_alerts(cursor, facility_id: str) -> Dict:
    """Get alerts specific to this facility."""

    # rn,just reorder suggestions based on low stock
    # TODO: REFACTOR????
    # TODO: If predictive reordering is to be triggered by the llm, figure out if this is well adapted to the feature?
    # SO is flow going to be - this alert fires, llm runs its reasoning? or sepearate em
    # logic duplicates low_stock query issh but as actionable alerts
    cursor.execute(
        """
        SELECT
            m.med_id,
            m.generic_name as medication_name,
            m.base_demand,
            SUM(i.quantity) as current_stock,
            MIN(i.reorder_point) as reorder_point
        FROM inventory i
        JOIN batches b ON i.batch_id = b.batch_id
        JOIN brands br ON b.brand_id = br.brand_id
        JOIN medications m ON br.med_id = m.med_id
        WHERE i.facility_id = ?
        GROUP BY m.med_id
        HAVING SUM(i.quantity) <= MIN(i.reorder_point)
    """,
        (facility_id,),
    )
    suggestions = []
    for row in cursor.fetchall():
        suggestions.append(
            {
                "type": "REORDER_NEEDED",
                "medication": row["medication_name"],
                "message": f"Stock ({row['current_stock']}) below reorder point ({row['reorder_point']})",
            }
        )

    return {"reorder_suggestions": suggestions}
