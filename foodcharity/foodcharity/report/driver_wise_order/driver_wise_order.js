// Copyright (c) 2024, Aadhil and contributors
// For license information, please see license.txt

frappe.query_reports["Driver wise order"] = {
	"filters": [
		{
			"fieldname": "assigned_volunteer",
			"label": __("Volunteer"),
			"fieldtype": "Link",
			"options": "Volunteer",
		}
	]
};
