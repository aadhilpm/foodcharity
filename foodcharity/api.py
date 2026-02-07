import frappe
import requests
from frappe.utils import formatdate

BASE_URL = "https://qnas.qa/"


@frappe.whitelist(allow_guest=True)
def get_event_settings():
    """Get event configuration for the order page"""
    try:
        settings = frappe.get_single("Foodcharity Settings")
        event_date_formatted = ""
        if settings.event_date:
            event_date_formatted = formatdate(settings.event_date, "EEEE, d MMMM yyyy")
        return {
            "enabled": bool(settings.event_enabled),
            "name": settings.event_name or "Biriyani Challenge 2026",
            "subtitle": settings.event_subtitle or "Thanal Milestone CDC",
            "date": event_date_formatted,
            "raw_date": str(settings.event_date) if settings.event_date else ""
        }
    except Exception:
        return {
            "enabled": True,
            "name": "Biriyani Challenge 2026",
            "subtitle": "Thanal Milestone CDC",
            "date": "Friday, 13 February 2026",
            "raw_date": "2026-02-13"
        }


def get_qnas_headers():
    """Get QNAS API headers from settings"""
    try:
        settings = frappe.get_single("Foodcharity Settings")
        if settings.qnas_enabled and settings.qnas_api_token and settings.qnas_api_domain:
            return {
                "X-Token": settings.get_password("qnas_api_token"),
                "X-Domain": settings.qnas_api_domain,
                "Accept": "application/json"
            }
    except Exception:
        pass
    return {"Accept": "application/json"}


def has_local_data():
    """Check if local QNAS data exists"""
    return frappe.db.count("Zone") > 0


@frappe.whitelist(allow_guest=True)
def get_zones():
    """Fetch zones - from local DB if synced, otherwise from API"""
    # Try local data first
    if has_local_data():
        zones = frappe.get_all(
            "Zone",
            fields=["zone_number", "zone_name_en", "zone_name_ar"],
            order_by="zone_number asc"
        )
        return [
            {
                "value": z.zone_number,
                "label": f"{z.zone_number} - {z.zone_name_en} ({z.zone_name_ar})"
            }
            for z in zones
        ]

    # Fallback to API
    try:
        headers = get_qnas_headers()
        response = requests.get(f"{BASE_URL}get_zones", headers=headers)
        response.raise_for_status()
        zones = response.json()
        return [
            {
                "value": str(z["zone_number"]),
                "label": f"{z['zone_number']} - {z['zone_name_en']} ({z['zone_name_ar']})"
            }
            for z in zones
        ]
    except requests.exceptions.RequestException as e:
        frappe.log_error(f"Error fetching zones: {str(e)}")
        return []


@frappe.whitelist(allow_guest=True)
def get_streets(zone_number):
    """Fetch streets - from local DB if synced, otherwise from API"""
    # Try local data first
    if has_local_data():
        streets = frappe.get_all(
            "Street",
            filters={"zone": zone_number},
            fields=["street_number", "street_name_en", "street_name_ar"],
            order_by="street_number asc"
        )
        return [
            {
                "value": s.street_number,
                "label": f"{s.street_number} - {s.street_name_en or ''} ({s.street_name_ar or ''})"
            }
            for s in streets
        ]

    # Fallback to API
    try:
        headers = get_qnas_headers()
        response = requests.get(f"{BASE_URL}get_streets/{zone_number}", headers=headers)
        response.raise_for_status()
        streets = response.json()
        return [
            {
                "value": str(s["street_number"]),
                "label": f"{s['street_number']} - {s['street_name_en']} ({s['street_name_ar']})"
            }
            for s in streets
        ]
    except requests.exceptions.RequestException as e:
        frappe.log_error(f"Error fetching streets: {str(e)}")
        return []


@frappe.whitelist(allow_guest=True)
def get_buildings(zone_number, street_number):
    """Fetch buildings - from local DB if available, otherwise from API and save locally"""
    # Try local data first
    buildings = frappe.get_all(
        "Building",
        filters={"zone": zone_number, "street_number": street_number},
        fields=["building_number", "latitude", "longitude"],
        order_by="building_number asc"
    )

    if buildings:
        return [
            {
                "value": b.building_number,
                "label": b.building_number,
                "x": b.latitude,
                "y": b.longitude
            }
            for b in buildings
        ]

    # Not found locally, fetch from QNAS API and save
    try:
        headers = get_qnas_headers()
        response = requests.get(f"{BASE_URL}get_buildings/{zone_number}/{street_number}", headers=headers)
        response.raise_for_status()
        api_buildings = response.json()

        # Save buildings locally for future use
        save_buildings_locally(zone_number, street_number, api_buildings)

        return [
            {
                "value": str(b["building_number"]),
                "label": f"{b['building_number']}",
                "x": b["x"],
                "y": b["y"]
            }
            for b in api_buildings
        ]
    except requests.exceptions.RequestException as e:
        frappe.log_error(f"Error fetching buildings: {str(e)}")
        return []


def save_buildings_locally(zone_number, street_number, buildings):
    """Save buildings fetched from QNAS API to local doctypes"""
    try:
        # Ensure Street exists
        street_name = f"{zone_number}-{street_number}"
        if not frappe.db.exists("Street", street_name):
            street_doc = frappe.get_doc({
                "doctype": "Street",
                "name": street_name,
                "zone": zone_number,
                "street_number": street_number
            })
            street_doc.insert(ignore_permissions=True)

        # Save each building
        for b in buildings:
            building_number = str(b.get("building_number"))
            building_name = f"{zone_number}-{street_number}-{building_number}"

            if not frappe.db.exists("Building", building_name):
                building_doc = frappe.get_doc({
                    "doctype": "Building",
                    "name": building_name,
                    "zone": zone_number,
                    "street": street_name,
                    "street_number": street_number,
                    "building_number": building_number,
                    "latitude": b.get("x"),
                    "longitude": b.get("y")
                })
                building_doc.insert(ignore_permissions=True)

        frappe.db.commit()
    except Exception as e:
        frappe.log_error(f"Error saving buildings locally: {str(e)}")


@frappe.whitelist(allow_guest=True)
def get_location(zone_number, street_number, building_number):
    """Fetch coordinates for a specific building"""
    # Try local data first
    if has_local_data():
        building = frappe.db.get_value(
            "Building",
            {"zone": zone_number, "street_number": street_number, "building_number": building_number},
            ["latitude", "longitude"],
            as_dict=True
        )
        if building:
            return {"latitude": building.latitude, "longitude": building.longitude}

    # Fallback to API
    try:
        headers = get_qnas_headers()
        response = requests.get(f"{BASE_URL}get_buildings/{zone_number}/{street_number}", headers=headers)
        response.raise_for_status()
        buildings = response.json()
        for building in buildings:
            if building["building_number"] == str(building_number):
                return {"latitude": building["x"], "longitude": building["y"]}
        return {}
    except requests.exceptions.RequestException as e:
        frappe.log_error(f"Error fetching location: {str(e)}")
        return {}


@frappe.whitelist(allow_guest=True)
def get_building_coordinates(zone_number, street_number, building_number):
    """Fetch building coordinates - from local DB or QNAS API, saves locally if fetched from API"""
    # Try local data first
    building = frappe.db.get_value(
        "Building",
        {"zone": zone_number, "street_number": street_number, "building_number": building_number},
        ["latitude", "longitude"],
        as_dict=True
    )

    if building and building.latitude and building.longitude:
        return {"latitude": building.latitude, "longitude": building.longitude}

    # Fetch from QNAS API
    try:
        headers = get_qnas_headers()
        response = requests.get(f"{BASE_URL}get_buildings/{zone_number}/{street_number}", headers=headers)
        response.raise_for_status()
        api_buildings = response.json()

        for b in api_buildings:
            if str(b.get("building_number")) == str(building_number):
                latitude = b.get("x")
                longitude = b.get("y")

                if latitude and longitude:
                    # Save this building locally
                    save_single_building_locally(zone_number, street_number, building_number, latitude, longitude)
                    return {"latitude": latitude, "longitude": longitude}

        return {}
    except Exception as e:
        frappe.log_error(f"Error fetching building coordinates: {str(e)}")
        return {}


def save_single_building_locally(zone_number, street_number, building_number, latitude, longitude):
    """Save a single building to local doctype"""
    try:
        # Ensure Street exists
        street_name = f"{zone_number}-{street_number}"
        if not frappe.db.exists("Street", street_name):
            street_doc = frappe.get_doc({
                "doctype": "Street",
                "name": street_name,
                "zone": zone_number,
                "street_number": street_number
            })
            street_doc.insert(ignore_permissions=True)

        # Create Building
        building_name = f"{zone_number}-{street_number}-{building_number}"
        if not frappe.db.exists("Building", building_name):
            building_doc = frappe.get_doc({
                "doctype": "Building",
                "name": building_name,
                "zone": zone_number,
                "street": street_name,
                "street_number": street_number,
                "building_number": building_number,
                "latitude": latitude,
                "longitude": longitude
            })
            building_doc.insert(ignore_permissions=True)
            frappe.db.commit()
    except Exception as e:
        frappe.log_error(f"Error saving building locally: {str(e)}")


@frappe.whitelist(allow_guest=True)
def get_doctype_fields(doctype):
    """Get doctype field metadata for dynamic form rendering"""
    meta = frappe.get_meta(doctype)
    fields = []
    for field in meta.fields:
        fields.append({
            "fieldname": field.fieldname,
            "fieldtype": field.fieldtype,
            "label": field.label,
            "options": field.options,
            "reqd": field.reqd,
            "depends_on": field.depends_on,
            "mandatory_depends_on": field.mandatory_depends_on,
            "default": field.default,
            "description": field.description,
            "read_only": field.read_only,
            "hidden": field.hidden
        })
    return fields


@frappe.whitelist(allow_guest=True)
def create_guest_order(data):
    """Create an order from public form (guest access)"""
    import json
    if isinstance(data, str):
        data = json.loads(data)

    order = frappe.get_doc({"doctype": "Orders", **data})
    order.insert(ignore_permissions=True)
    frappe.db.commit()

    return {"success": True, "order_id": order.name}


@frappe.whitelist(allow_guest=True)
def search_orders_by_phone(phone):
    """Search orders by phone number (mobile or whatsapp)"""
    if not phone or len(phone) < 8:
        return []

    orders = frappe.get_all(
        "Orders",
        filters=[
            ["Orders", "mobile", "like", f"%{phone}%"]
        ],
        or_filters=[
            ["Orders", "whatsapp_number", "like", f"%{phone}%"]
        ],
        fields=[
            "name", "name1", "mobile", "whatsapp_number", "order_type",
            "no_of_biriyani", "contribution_amount", "accommodation_area",
            "zone_number", "street_number", "building_number", "door_number",
            "accommodation_type", "compound_name", "creation",
            "order_status", "collected_amount"
        ],
        order_by="creation desc",
        limit=10
    )
    return orders


@frappe.whitelist(allow_guest=True)
def get_order(order_id):
    """Get a single order by ID"""
    if not order_id:
        return None

    try:
        order = frappe.get_doc("Orders", order_id)
        result = {
            "name": order.name,
            "name1": order.name1,
            "mobile": order.mobile,
            "whatsapp_number": order.whatsapp_number,
            "order_type": order.order_type,
            "no_of_biriyani": order.no_of_biriyani,
            "contribution_amount": order.contribution_amount,
            "accommodation_area": order.accommodation_area,
            "zone_number": order.zone_number,
            "street_number": order.street_number,
            "building_number": order.building_number,
            "door_number": order.door_number,
            "accommodation_type": order.accommodation_type,
            "compound_name": order.compound_name,
            "coordinate": order.coordinate,
            "assigned_volunteer": order.assigned_volunteer,
            "creation": order.creation
        }
        # Include driver details if assigned
        if order.assigned_volunteer:
            volunteer = frappe.get_doc("Volunteer", order.assigned_volunteer)
            result["driver"] = {
                "id": volunteer.name,
                "name": volunteer.full_name,
                "mobile": volunteer.mobile_number
            }
        return result
    except frappe.DoesNotExistError:
        return None


@frappe.whitelist(allow_guest=True)
def update_guest_order(order_id, data):
    """Update an existing order"""
    import json
    if isinstance(data, str):
        data = json.loads(data)

    if not order_id:
        return {"success": False, "error": "Order ID is required"}

    try:
        order = frappe.get_doc("Orders", order_id)
        order.update(data)
        order.save(ignore_permissions=True)
        frappe.db.commit()
        return {"success": True, "order_id": order.name}
    except frappe.DoesNotExistError:
        return {"success": False, "error": "Order not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist(allow_guest=True)
def driver_login(mobile, password):
    """Authenticate driver by mobile and password"""
    if not mobile or not password:
        return {"success": False, "error": "Mobile and password are required"}

    # Strip +974 if present
    if mobile.startswith("+974"):
        mobile = mobile[4:]

    volunteers = frappe.get_all(
        "Volunteer",
        filters=[
            ["mobile_number", "like", f"%{mobile}%"],
            ["interest", "=", "Driver"]
        ],
        fields=["name", "full_name", "mobile_number"]
    )

    if not volunteers:
        return {"success": False, "error": "Driver not found"}

    volunteer = frappe.get_doc("Volunteer", volunteers[0].name)

    try:
        stored_password = volunteer.get_password("driver_password")
    except Exception:
        stored_password = None

    if not stored_password:
        return {"success": False, "error": "Password not set for this driver"}

    if stored_password != password:
        return {"success": False, "error": "Invalid password"}

    return {
        "success": True,
        "driver": {
            "id": volunteer.name,
            "name": volunteer.full_name,
            "mobile": volunteer.mobile_number
        }
    }


@frappe.whitelist(allow_guest=True)
def get_driver_orders(driver_id):
    """Get all orders assigned to a driver"""
    if not driver_id:
        return {"orders": [], "per_biriyani_charge": 0}

    # Get per biriyani charge from settings
    try:
        settings = frappe.get_single("Foodcharity Settings")
        per_biriyani_charge = float(settings.per_biriyani_charge or 20)
    except Exception:
        per_biriyani_charge = 20

    orders = frappe.get_all(
        "Orders",
        filters={"assigned_volunteer": driver_id},
        fields=[
            "name", "name1", "mobile", "whatsapp_number", "order_type",
            "no_of_biriyani", "accommodation_area", "zone_number",
            "street_number", "building_number", "door_number",
            "accommodation_type", "compound_name", "coordinate", "creation",
            "collected_amount", "contribution_amount",
            "location_request_sent", "thank_you_sent", "order_status", "remark"
        ],
        order_by="creation desc"
    )

    # Calculate total amount and fetch coordinates for each order
    for order in orders:
        biriyani_count = order.get("no_of_biriyani") or 0
        order["total_amount"] = biriyani_count * per_biriyani_charge
        order["collected_amount"] = order.get("collected_amount") or 0

        # Fetch coordinates from Building doctype if zone, street, building are available
        if order.get("zone_number") and order.get("street_number") and order.get("building_number"):
            building = frappe.db.get_value(
                "Building",
                {
                    "zone": order.get("zone_number"),
                    "street_number": order.get("street_number"),
                    "building_number": order.get("building_number")
                },
                ["latitude", "longitude"],
                as_dict=True
            )
            if building and building.latitude and building.longitude:
                order["coordinate"] = f"{building.latitude},{building.longitude}"

    return {"orders": orders, "per_biriyani_charge": per_biriyani_charge}


@frappe.whitelist(allow_guest=True)
def update_collected_amount(order_id, collected_amount):
    """Update collected amount for an order"""
    if not order_id:
        return {"success": False, "error": "Order ID required"}

    try:
        collected = float(collected_amount or 0)
        frappe.db.set_value("Orders", order_id, "collected_amount", collected)
        frappe.db.commit()
        return {"success": True, "collected_amount": collected}
    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist(allow_guest=True)
def update_message_status(order_id, field, value=1):
    """Update message sent status (location_request_sent or thank_you_sent)"""
    if not order_id:
        return {"success": False, "error": "Order ID required"}

    if field not in ["location_request_sent", "thank_you_sent"]:
        return {"success": False, "error": "Invalid field"}

    try:
        frappe.db.set_value("Orders", order_id, field, int(value))
        frappe.db.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist(allow_guest=True)
def get_all_drivers():
    """Get all volunteers who are drivers with their order stats"""
    drivers = frappe.get_all(
        "Volunteer",
        filters={"interest": "Driver"},
        fields=["name", "full_name", "mobile_number", "remark", "preferred_delivery_location"]
    )

    # Get per biriyani charge
    try:
        settings = frappe.get_single("Foodcharity Settings")
        per_biriyani_charge = float(settings.per_biriyani_charge or 20)
    except Exception:
        per_biriyani_charge = 20

    # Get order stats for each driver
    for driver in drivers:
        orders = frappe.get_all(
            "Orders",
            filters={"assigned_volunteer": driver.name},
            fields=["no_of_biriyani", "collected_amount"]
        )
        driver["order_count"] = len(orders)
        driver["total_biriyani"] = sum(o.no_of_biriyani or 0 for o in orders)
        driver["total_amount"] = driver["total_biriyani"] * per_biriyani_charge
        driver["total_collected"] = sum(o.collected_amount or 0 for o in orders)

    return {"drivers": drivers, "per_biriyani_charge": per_biriyani_charge}


@frappe.whitelist(allow_guest=True)
def get_unassigned_orders():
    """Get all orders without a driver assigned"""
    orders = frappe.get_all(
        "Orders",
        filters=[
            ["assigned_volunteer", "is", "not set"]
        ],
        or_filters=[
            ["assigned_volunteer", "=", ""],
            ["assigned_volunteer", "is", "not set"]
        ],
        fields=[
            "name", "name1", "mobile", "whatsapp_number", "order_type",
            "no_of_biriyani", "accommodation_area", "zone_number",
            "street_number", "building_number", "door_number", "creation"
        ],
        order_by="creation desc"
    )
    return orders


@frappe.whitelist(allow_guest=True)
def get_all_orders_for_coordinator():
    """Get all orders with driver info for coordinator view"""
    orders = frappe.get_all(
        "Orders",
        fields=[
            "name", "name1", "mobile", "whatsapp_number", "order_type",
            "no_of_biriyani", "accommodation_area", "zone_number",
            "street_number", "building_number", "door_number",
            "assigned_volunteer", "collected_amount", "creation", "order_status", "remark"
        ],
        order_by="creation desc"
    )

    # Get driver names
    driver_names = {}
    for order in orders:
        if order.assigned_volunteer and order.assigned_volunteer not in driver_names:
            vol = frappe.db.get_value("Volunteer", order.assigned_volunteer, "full_name")
            driver_names[order.assigned_volunteer] = vol or order.assigned_volunteer
        order["driver_name"] = driver_names.get(order.assigned_volunteer, "")

    return orders


@frappe.whitelist(allow_guest=True)
def assign_order_to_driver(order_id, driver_id):
    """Assign an order to a driver"""
    if not order_id:
        return {"success": False, "error": "Order ID required"}

    try:
        frappe.db.set_value("Orders", order_id, "assigned_volunteer", driver_id or None)
        # Update status based on assignment
        if driver_id:
            frappe.db.set_value("Orders", order_id, "order_status", "Assigned")
        else:
            frappe.db.set_value("Orders", order_id, "order_status", "Pending")
        frappe.db.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist(allow_guest=True)
def bulk_assign_orders(order_ids, driver_id):
    """Assign multiple orders to a driver"""
    import json
    if isinstance(order_ids, str):
        order_ids = json.loads(order_ids)

    if not order_ids:
        return {"success": False, "error": "No orders provided"}

    try:
        for order_id in order_ids:
            frappe.db.set_value("Orders", order_id, "assigned_volunteer", driver_id or None)
            # Update status to Assigned if driver is set
            if driver_id:
                frappe.db.set_value("Orders", order_id, "order_status", "Assigned")
            else:
                frappe.db.set_value("Orders", order_id, "order_status", "Pending")
        frappe.db.commit()
        return {"success": True, "count": len(order_ids)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist(allow_guest=True)
def coordinator_login(password):
    """Authenticate coordinator by password"""
    if not password:
        return {"success": False, "error": "Password is required"}

    try:
        settings = frappe.get_single("Foodcharity Settings")
        stored_password = settings.get_password("coordinator_password")

        if not stored_password:
            return {"success": False, "error": "Coordinator password not set"}

        if stored_password == password:
            return {"success": True}
        else:
            return {"success": False, "error": "Invalid password"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist(allow_guest=True)
def update_order_status(order_id, status):
    """Update order status"""
    if not order_id:
        return {"success": False, "error": "Order ID required"}

    valid_statuses = ["Pending", "Assigned", "Out for Delivery", "Delivered", "Collected"]
    if status not in valid_statuses:
        return {"success": False, "error": "Invalid status"}

    try:
        frappe.db.set_value("Orders", order_id, "order_status", status)
        frappe.db.commit()
        return {"success": True, "status": status}
    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist(allow_guest=True)
def update_order_remark(order_id, remark):
    """Update order remark"""
    if not order_id:
        return {"success": False, "error": "Order ID required"}

    try:
        frappe.db.set_value("Orders", order_id, "remark", remark or "")
        frappe.db.commit()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}
