"""
file containing tools the llm needs for action/intelligence and might be used for investigation

TODO: IMPLEMENT TOOLS FOR PREDICTIVE REASONING
- Market trends (external API)
- Port congestion (external API)
- Predictive reordering
"""

from typing import List, Dict
from medguard.db.database import get_connection_to_db
from medguard.agent.registry import registry


@registry.register
def trace_batch_journey(batch_id: str) -> List[Dict]:
    """
    Trace the complete movement history of a batch for counterfeit investigation.
    Shows where the batch has been and how it moved through the supply chain.

    Use this tool when investigating anomalies to understand the full journey
    of a suspicious batch before making QUARANTINE or ESCALATE decisions.

    Args:
        batch_id: The batch ID to trace.

    Returns:
        Chronological list of all movements for this batch.
    """
    conn = get_connection_to_db()
    cursor = conn.cursor()

    # get batch details first
    cursor.execute(
        """
        SELECT b.*, br.brand_name, m.name as manufacturer
        FROM batches b
        JOIN brands br ON b.brand_id = br.brand_id
        LEFT JOIN companies m ON br.manufacturer_id = m.company_id
        WHERE b.batch_id = ?
        """,
        (batch_id,),
    )
    batch_info = cursor.fetchone()

    if not batch_info:
        conn.close()
        return [{"error": "Batch not found"}]

    # get all movements
    cursor.execute(
        """
        SELECT m.*, f.name as facility_name, f.city
        FROM movements m
        JOIN facilities f ON m.facility_id = f.facility_id
        WHERE m.batch_id = ?
        ORDER BY m.timestamp ASC
        """,
        (batch_id,),
    )
    movements = cursor.fetchall()
    conn.close()

    journey = [
        {
            "timestamp": row["timestamp"],
            "facility_id": row["facility_id"],
            "facility_name": row["facility_name"],
            "city": row["city"],
            "movement_type": row["movement_type"],
            "quantity_change": row["quantity_change"],
            "quantity_after": row["quantity_after"],
            "reason": row["reason"],
        }
        for row in movements
    ]

    return journey
