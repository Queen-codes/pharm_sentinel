from medguard.db.database import get_connection_to_db

query_function_declaration = {
    "name": "query_inventory",
    "description": "Get current inventory level for a specific medication at a specific facility. Use this to check stock before recommending transfers or to verify quantities",
    "parameters": {
        "type": "object",
        "properties": {
            "facility_id": {
                "type": "string",
                "description": "system-generated identifier of the facility to query",
            },
            # end of prop 1 definition
            "medication_id": {
                "type": "string",
                "description": "system-generated identifier of the medication to check",
            },
            # end of prop 2 definition
        },
        # end of props
        "required": ["facility_id", "medication_id"],
    },
    # end of parameters function
}


def query_inventory(facility_id: str, medication_id: str) -> dict:
    """
    Get current inventory level for a specific medication at a specific facility.

    :param facility_id: specific id of the facilities that would be queried
    :type facility_id: str
    :param medication_id: id of the medication
    :type medication_id: str
    """
    conn = get_connection_to_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT SUM(inventory.quantity) AS total_quantity
        FROM inventory
        JOIN batches ON inventory.batch_id = batches.batch_id
        JOIN brands ON batches.brand_id = brands.brand_id
        WHERE inventory.facility_id = ?
          AND brands.med_id = ?
        """,
        (facility_id, medication_id),
    )

    row = cursor.fetchone()
    conn.close()

    return {
        "facility_id": facility_id,
        "medication_id": medication_id,
        "quantity": row["total_quantity"] or 0,
    }
