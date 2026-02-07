# Copyright (c) 2024, Aadhil and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
import requests


class FoodcharitySettings(Document):
	@frappe.whitelist()
	def sync_qnas_data(self):
		"""Sync all QNAS data (zones, streets, buildings) to local doctypes"""
		# Reset the street index when doing full sync
		self.last_synced_street_index = 0
		self.save(ignore_permissions=True)
		frappe.db.commit()

		frappe.enqueue(
			sync_all_qnas_data,
			queue="long",
			timeout=3600,
			job_id="sync_qnas_data"
		)
		frappe.msgprint("QNAS data sync started in background. This may take a while.")

	@frappe.whitelist()
	def sync_buildings_only(self):
		"""Sync only buildings, resuming from last position"""
		start_index = self.last_synced_street_index or 0
		frappe.enqueue(
			sync_buildings_only,
			queue="long",
			timeout=3600,
			job_id="sync_buildings_only",
			start_index=start_index
		)
		frappe.msgprint(f"Building sync started from street index {start_index}. This may take a while.")


def get_qnas_headers():
	"""Get QNAS API headers from settings"""
	settings = frappe.get_single("Foodcharity Settings")
	if settings.qnas_enabled and settings.qnas_api_token and settings.qnas_api_domain:
		return {
			"X-Token": settings.get_password("qnas_api_token"),
			"X-Domain": settings.qnas_api_domain,
			"Accept": "application/json"
		}
	return {"Accept": "application/json"}


def sync_all_qnas_data():
	"""Background job to sync all QNAS data"""
	import time

	headers = get_qnas_headers()
	base_url = "https://qnas.qa/"

	# Sync zones
	frappe.publish_realtime("qnas_sync_progress", {"message": "Fetching zones..."})

	try:
		response = requests.get(f"{base_url}get_zones", headers=headers)
		response.raise_for_status()
		zones = response.json()

		zone_count = 0
		for z in zones:
			zone_number = str(z["zone_number"])
			if not frappe.db.exists("Zone", zone_number):
				frappe.get_doc({
					"doctype": "Zone",
					"zone_number": zone_number,
					"zone_name_en": z.get("zone_name_en", ""),
					"zone_name_ar": z.get("zone_name_ar", "")
				}).insert(ignore_permissions=True)
			else:
				frappe.db.set_value("Zone", zone_number, {
					"zone_name_en": z.get("zone_name_en", ""),
					"zone_name_ar": z.get("zone_name_ar", "")
				})
			zone_count += 1

		frappe.db.commit()
		frappe.publish_realtime("qnas_sync_progress", {"message": f"Synced {zone_count} zones. Fetching streets..."})

		# Sync streets for each zone
		street_count = 0
		for z in zones:
			zone_number = str(z["zone_number"])
			time.sleep(0.5)  # Rate limiting

			try:
				response = requests.get(f"{base_url}get_streets/{zone_number}", headers=headers)
				response.raise_for_status()
				streets = response.json()

				for s in streets:
					street_number = str(s["street_number"])
					street_name = f"{zone_number}-{street_number}"

					if not frappe.db.exists("Street", street_name):
						frappe.get_doc({
							"doctype": "Street",
							"zone": zone_number,
							"street_number": street_number,
							"street_name_en": s.get("street_name_en", ""),
							"street_name_ar": s.get("street_name_ar", "")
						}).insert(ignore_permissions=True)
					else:
						frappe.db.set_value("Street", street_name, {
							"street_name_en": s.get("street_name_en", ""),
							"street_name_ar": s.get("street_name_ar", "")
						})
					street_count += 1

				frappe.db.commit()
			except Exception as e:
				frappe.log_error(f"Error syncing streets for zone {zone_number}: {str(e)}")

		frappe.publish_realtime("qnas_sync_progress", {"message": f"Synced {street_count} streets. Fetching buildings..."})

		# Sync buildings for each street
		building_count = 0
		streets_list = frappe.get_all("Street", fields=["name", "zone", "street_number"])

		for idx, street in enumerate(streets_list):
			time.sleep(0.5)  # Rate limiting

			try:
				response = requests.get(
					f"{base_url}get_buildings/{street.zone}/{street.street_number}",
					headers=headers
				)
				response.raise_for_status()
				buildings = response.json()

				for b in buildings:
					building_number = str(b["building_number"])
					building_name = f"{street.zone}-{street.street_number}-{building_number}"

					if not frappe.db.exists("Building", building_name):
						frappe.get_doc({
							"doctype": "Building",
							"zone": street.zone,
							"street": street.name,
							"street_number": street.street_number,
							"building_number": building_number,
							"latitude": b.get("x"),
							"longitude": b.get("y")
						}).insert(ignore_permissions=True)
					else:
						frappe.db.set_value("Building", building_name, {
							"latitude": b.get("x"),
							"longitude": b.get("y")
						})
					building_count += 1

				if idx % 10 == 0:
					frappe.db.commit()
					frappe.publish_realtime("qnas_sync_progress", {
						"message": f"Synced {building_count} buildings ({idx + 1}/{len(streets_list)} streets)..."
					})

			except Exception as e:
				frappe.log_error(f"Error syncing buildings for street {street.name}: {str(e)}")

		frappe.db.commit()

		# Update settings with sync status
		settings = frappe.get_single("Foodcharity Settings")
		settings.last_synced = now_datetime()
		settings.total_zones = frappe.db.count("Zone")
		settings.total_streets = frappe.db.count("Street")
		settings.total_buildings = frappe.db.count("Building")
		settings.save(ignore_permissions=True)
		frappe.db.commit()

		frappe.publish_realtime("qnas_sync_progress", {
			"message": f"Sync complete! {zone_count} zones, {street_count} streets, {building_count} buildings.",
			"complete": True
		})

	except Exception as e:
		frappe.log_error(f"QNAS sync error: {str(e)}")
		frappe.publish_realtime("qnas_sync_progress", {
			"message": f"Error: {str(e)}",
			"error": True
		})


def sync_buildings_only(start_index=0):
	"""Background job to sync only buildings, resuming from last position"""
	import time

	headers = get_qnas_headers()
	base_url = "https://qnas.qa/"

	try:
		# Get all streets from local DB
		streets_list = frappe.get_all("Street", fields=["name", "zone", "street_number"], order_by="name asc")
		total_streets = len(streets_list)

		if start_index >= total_streets:
			frappe.publish_realtime("qnas_sync_progress", {
				"message": "All streets already synced. Reset index to sync again.",
				"complete": True
			})
			return

		frappe.publish_realtime("qnas_sync_progress", {
			"message": f"Resuming from street {start_index + 1}/{total_streets}..."
		})

		building_count = 0
		current_index = start_index

		for idx, street in enumerate(streets_list[start_index:], start=start_index):
			time.sleep(0.5)  # Rate limiting
			current_index = idx

			try:
				response = requests.get(
					f"{base_url}get_buildings/{street.zone}/{street.street_number}",
					headers=headers
				)
				response.raise_for_status()
				buildings = response.json()

				for b in buildings:
					building_number = str(b["building_number"])
					building_name = f"{street.zone}-{street.street_number}-{building_number}"

					if not frappe.db.exists("Building", building_name):
						frappe.get_doc({
							"doctype": "Building",
							"zone": street.zone,
							"street": street.name,
							"street_number": street.street_number,
							"building_number": building_number,
							"latitude": b.get("x"),
							"longitude": b.get("y")
						}).insert(ignore_permissions=True)
					else:
						frappe.db.set_value("Building", building_name, {
							"latitude": b.get("x"),
							"longitude": b.get("y")
						})
					building_count += 1

				# Save progress every 10 streets
				if idx % 10 == 0:
					frappe.db.commit()
					# Update the last synced index
					frappe.db.set_value("Foodcharity Settings", "Foodcharity Settings", {
						"last_synced_street_index": idx + 1,
						"synced_buildings": building_count
					})
					frappe.db.commit()
					frappe.publish_realtime("qnas_sync_progress", {
						"message": f"Synced {building_count} buildings ({idx + 1}/{total_streets} streets)..."
					})

			except Exception as e:
				frappe.log_error(f"Error syncing buildings for street {street.name}: {str(e)}")
				# Save current position before error
				frappe.db.set_value("Foodcharity Settings", "Foodcharity Settings", {
					"last_synced_street_index": idx,
					"synced_buildings": building_count
				})
				frappe.db.commit()

		frappe.db.commit()

		# Update settings with sync status
		settings = frappe.get_single("Foodcharity Settings")
		settings.last_synced = now_datetime()
		settings.last_synced_street_index = total_streets  # Mark as complete
		settings.total_buildings = frappe.db.count("Building")
		settings.synced_buildings = building_count
		settings.save(ignore_permissions=True)
		frappe.db.commit()

		frappe.publish_realtime("qnas_sync_progress", {
			"message": f"Building sync complete! {building_count} buildings synced.",
			"complete": True
		})

	except Exception as e:
		frappe.log_error(f"Building sync error: {str(e)}")
		frappe.publish_realtime("qnas_sync_progress", {
			"message": f"Error: {str(e)}",
			"error": True
		})
