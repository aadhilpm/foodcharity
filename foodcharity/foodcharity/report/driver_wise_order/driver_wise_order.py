import frappe
from frappe import _

def execute(filters=None):
    columns = [
        {
            "label": _("Job ID"),
            "fieldname": "job_id",
            "fieldtype": "Link",
            "options": "Orders",
            "width": 100
        },
        {
            "label": _("Volunteer"),
            "fieldname": "assigned_volunteer",
            "fieldtype": "Link",
            "options": "Volunteer",
            "width": 120
        },
        {
            "label": _("Volunteer Mobile"),
            "fieldname": "volunteer_mobile",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Full Name"),
            "fieldname": "job_name",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": _("Mobile"),
            "fieldname": "job_mobile",
            "fieldtype": "Data",
            "width": 110
        },
        {
            "label": _("Area"),
            "fieldname": "job_area",
            "fieldtype": "Data",
            "width": 130
        },
        {
            "label": _("Zone"),
            "fieldname": "job_zone",
            "fieldtype": "Data",
            "width": 60
        },
        {
            "label": _("Street"),
            "fieldname": "street_number",
            "fieldtype": "Data",
            "width": 60
        },
        {
            "label": _("Building"),
            "fieldname": "job_build",
            "fieldtype": "Data",
            "width": 70
        },
        {
            "label": _("Door"),
            "fieldname": "door_number",
            "fieldtype": "Data",
            "width": 60
        },
        {
            "label": _("Compound Name"),
            "fieldname": "compound_name",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("No Of Biriyani"),
            "fieldname": "job_no",
            "fieldtype": "Int",
            "width": 100
        },
        {
            "label": _("Contribution"),
            "fieldname": "contribution_amount",
            "fieldtype": "Currency",
            "width": 100
        },
        {
            "label": _("Collected"),
            "fieldname": "collected_amount",
            "fieldtype": "Currency",
            "width": 100
        },
        {
            "label": _("Extra Amount"),
            "fieldname": "extra_amount",
            "fieldtype": "Currency",
            "width": 100
        },
        {
            "label": _("Status"),
            "fieldname": "order_status",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Remark"),
            "fieldname": "remark",
            "fieldtype": "Data",
            "width": 150
        }
    ]

    conditions, values = get_conditions(filters)
    query = """
        SELECT
            o.name AS job_id,
            o.assigned_volunteer,
            v.mobile_number AS volunteer_mobile,
            v.full_name AS volunteer_name,
            o.name1 AS job_name,
            o.mobile AS job_mobile,
            o.accommodation_area AS job_area,
            o.zone_number AS job_zone,
            o.street_number AS street_number,
            o.building_number AS job_build,
            o.door_number AS door_number,
            o.compound_name AS compound_name,
            o.no_of_biriyani AS job_no,
            o.contribution_amount,
            o.collected_amount,
            o.order_status,
            o.remark,
            o.coordinate
        FROM
            `tabOrders` o
        LEFT JOIN
            `tabVolunteer` v ON o.assigned_volunteer = v.name
        WHERE
            {conditions}
        ORDER BY
            o.accommodation_area ASC, o.zone_number ASC, o.street_number ASC
    """.format(conditions=conditions)

    data = frappe.db.sql(query, values, as_dict=True)

    # Calculate extra amount for each row
    for row in data:
        expected_amount = (row.get("job_no") or 0) * 20
        collected = row.get("collected_amount") or 0
        row["extra_amount"] = max(0, collected - expected_amount)

    return columns, data

def get_conditions(filters):
    conditions = ["1=1"]
    values = {}

    if filters.get("assigned_volunteer"):
        conditions.append("o.assigned_volunteer = %(assigned_volunteer)s")
        values["assigned_volunteer"] = filters.get("assigned_volunteer")

    return " AND ".join(conditions), values
