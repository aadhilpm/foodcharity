# Copyright (c) 2024, Aadhil and contributors
# For license information, please see license.txt

import frappe
import requests
from frappe.model.document import Document


class Orders(Document):
	def validate(self):
		self.update_coordinates()

	def update_coordinates(self):
		"""Fetch coordinates from Building doctype based on zone, street, and building number.
		If building not found locally, fetch from QNAS API and save it."""
		if not (self.zone_number and self.street_number and self.building_number):
			return

		# Try local Building doctype first
		building = frappe.db.get_value(
			"Building",
			{
				"zone": self.zone_number,
				"street_number": self.street_number,
				"building_number": self.building_number
			},
			["latitude", "longitude"],
			as_dict=True
		)

		if building and building.latitude and building.longitude:
			self.coordinate = f"{building.latitude},{building.longitude}"
			return

		# Not found locally, fetch from QNAS API
		try:
			settings = frappe.get_single("Foodcharity Settings")
			if not settings.qnas_enabled:
				return

			headers = {
				"X-Token": settings.get_password("qnas_api_token"),
				"X-Domain": settings.qnas_api_domain,
				"Accept": "application/json"
			}

			response = requests.get(
				f"https://qnas.qa/get_buildings/{self.zone_number}/{self.street_number}",
				headers=headers
			)
			response.raise_for_status()
			buildings = response.json()

			for b in buildings:
				if str(b.get("building_number")) == str(self.building_number):
					latitude = b.get("x")
					longitude = b.get("y")

					if latitude and longitude:
						# Save building to local doctype for future use
						self.save_building_locally(latitude, longitude)
						self.coordinate = f"{latitude},{longitude}"
					break

		except Exception as e:
			frappe.log_error(f"Error fetching building from QNAS: {str(e)}")

	def save_building_locally(self, latitude, longitude):
		"""Save building data to local Building doctype"""
		try:
			# Check if Street exists, create if not
			street_name = f"{self.zone_number}-{self.street_number}"
			if not frappe.db.exists("Street", street_name):
				street_doc = frappe.get_doc({
					"doctype": "Street",
					"name": street_name,
					"zone": self.zone_number,
					"street_number": self.street_number
				})
				street_doc.insert(ignore_permissions=True)

			# Create Building
			building_name = f"{self.zone_number}-{self.street_number}-{self.building_number}"
			if not frappe.db.exists("Building", building_name):
				building_doc = frappe.get_doc({
					"doctype": "Building",
					"name": building_name,
					"zone": self.zone_number,
					"street": street_name,
					"street_number": self.street_number,
					"building_number": self.building_number,
					"latitude": latitude,
					"longitude": longitude
				})
				building_doc.insert(ignore_permissions=True)
				frappe.db.commit()

		except Exception as e:
			frappe.log_error(f"Error saving building locally: {str(e)}")
