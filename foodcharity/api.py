import frappe
import requests

BASE_URL = "https://qnas.qa/"

@frappe.whitelist(allow_guest=True) 
def get_zones():
    """Fetch the list of zones in Qatar"""
    url = f"{BASE_URL}public/get_zones"
    try:
        response = requests.get(url)
        response.raise_for_status()
        zones = response.json()
        return [{"value": str(z["zone_number"]), "label": f"{z['zone_number']} - {z['zone_name_en']} ({z['zone_name_ar']})"} for z in zones]
    except requests.exceptions.RequestException as e:
        frappe.log_error(f"Error fetching zones: {str(e)}")
        return []

@frappe.whitelist(allow_guest=True) 
def get_streets(zone_number):
    """Fetch streets for a given zone"""
    url = f"{BASE_URL}get_streets/{zone_number}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        streets = response.json()
        return [{"value": str(s["street_number"]), "label": f"{s['street_number']} - {s['street_name_en']} ({s['street_name_ar']})"} for s in streets]
    except requests.exceptions.RequestException as e:
        frappe.log_error(f"Error fetching streets: {str(e)}")
        return []

@frappe.whitelist(allow_guest=True) 
def get_buildings(zone_number, street_number):
    """Fetch buildings for a given zone and street"""
    url = f"{BASE_URL}get_buildings/{zone_number}/{street_number}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        buildings = response.json()
        return [{"value": str(b["building_number"]), "label": f"{b['building_number']}", "x": b["x"], "y": b["y"]} for b in buildings]
    except requests.exceptions.RequestException as e:
        frappe.log_error(f"Error fetching buildings: {str(e)}")
        return []

@frappe.whitelist(allow_guest=True) 
def get_location(zone_number, street_number, building_number):
    """Fetch coordinates for a specific building"""
    url = f"{BASE_URL}get_buildings/{zone_number}/{street_number}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        buildings = response.json()
        for building in buildings:
            if building["building_number"] == str(building_number):
                return {"latitude": building["x"], "longitude": building["y"]}
        return {}
    except requests.exceptions.RequestException as e:
        frappe.log_error(f"Error fetching location: {str(e)}")
        return {}
