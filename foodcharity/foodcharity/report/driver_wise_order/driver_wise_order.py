import frappe
from frappe import _

def execute(filters=None):
    columns = [
        {
            "label": _("Job ID"),
            "fieldname": "job_id",
            "fieldtype": "Link",
            "options": "Orders",
            "width": 120
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
            "width": 120
        },
        {
            "label": _("Mobile"),
            "fieldname": "job_mobile",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Area"),
            "fieldname": "job_area",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Zone"),
            "fieldname": "job_zone",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Street"),
            "fieldname": "street_number",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Building"),
            "fieldname": "job_build",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Compound Name"),
            "fieldname": "compound_name",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Delivery Needed"),
            "fieldname": "delivery_needed",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("No Of Biriyani"),
            "fieldname": "job_no",
            "fieldtype": "Int",
            "width": 120
        },
        {
            "label": _("Total Cost"),
            "fieldname": "totalcost",
            "fieldtype": "Float",
            "width": 120
        },
        {
            "label": _("Extra Amount"),
            "fieldname": "extra_amount_received",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Remark"),
            "fieldname": "remark",
            "fieldtype": "Data",
            "width": 120
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
            o.compound_name AS compound_name,
            o.building_number AS job_build,
            o.delivery_needed,
            o.no_of_biriyani AS job_no
        FROM
            `tabOrders` o
        LEFT JOIN
            `tabVolunteer` v ON o.assigned_volunteer = v.name
        WHERE
            {conditions}
        ORDER BY
            o.accommodation_area ASC
    """.format(conditions=conditions)
    
    data = frappe.db.sql(query, values, as_dict=True)
    
    for row in data:
        row["totalcost"] = row.get("job_no", 0) * 20
        row["extra_amount_received"] = " " 
        row["remark"] = ""
    
    return columns, data

def get_conditions(filters):
    conditions = ["1=1"]
    values = {}

    if filters.get("assigned_volunteer"):
        conditions.append("o.assigned_volunteer = %(assigned_volunteer)s")
        values["assigned_volunteer"] = filters.get("assigned_volunteer")

    return " AND ".join(conditions), values
