# Copyright (c) 2024, sammish and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BahrainVATSetting(Document):
	pass


@frappe.whitelist()
def load_standard_template(docname):
	"""Load the standard Bahrain VAT return template"""
	doc = frappe.get_doc("Bahrain VAT Setting", docname)

	# Clear existing entries
	doc.bahrain_vat_sales_accounts = []
	doc.bahrain_vat_purchase_accounts = []

	# VAT on Sales template (Boxes 1-7)
	sales_template = [
		{"box_number": "1(a)", "title": "Standard rated sales at 5%"},
		{"box_number": "1(b)", "title": "Standard rated sales at 10%"},
		{"box_number": "2", "title": "Sales to registered taxpayers in other GCC States"},
		{"box_number": "3", "title": "Sales subject to domestic reverse charge mechanism"},
		{"box_number": "4", "title": "Zero rated domestic sales"},
		{"box_number": "5", "title": "Exports"},
		{"box_number": "6", "title": "Exempt sales"},
	]

	# VAT on Purchases template (Boxes 8-14)
	purchase_template = [
		{"box_number": "8(a)", "title": "Standard rated domestic purchases at 5%"},
		{"box_number": "8(b)", "title": "Standard rated domestic purchases at 10%"},
		{"box_number": "9", "title": "Imports subject to VAT paid at customs"},
		{"box_number": "10", "title": "Imports subject to VAT deferral at customs"},
		{
			"box_number": "11(a)",
			"title": "Imports subject to VAT accounted for through reverse charge mechanism at 5%",
		},
		{
			"box_number": "11(b)",
			"title": "Imports subject to VAT accounted for through reverse charge mechanism at 10%",
		},
		{"box_number": "12", "title": "Purchases subject to domestic reverse charge mechanism"},
		{"box_number": "13", "title": "Purchases from non-registered suppliers, zero-rated/exempt purchases"},
	]

	# Add sales accounts
	for item in sales_template:
		doc.append("bahrain_vat_sales_accounts", item)

	# Add purchase accounts
	for item in purchase_template:
		doc.append("bahrain_vat_purchase_accounts", item)

	doc.save()

	return {"message": "Standard Bahrain VAT template loaded successfully"}


@frappe.whitelist()
def create_tax_account_and_template(company, tax_rate, account_name, parent_account, template_name):
	"""Create Tax Account and Item Tax Template"""

	# Check if account already exists
	account_full_name = f"{account_name} - {frappe.get_cached_value('Company', company, 'abbr')}"
	if frappe.db.exists("Account", account_full_name):
		frappe.throw(f"Account '{account_full_name}' already exists")

	# Check if template already exists
	template_full_name = f"{template_name} - {frappe.get_cached_value('Company', company, 'abbr')}"
	if frappe.db.exists("Item Tax Template", template_full_name):
		frappe.throw(f"Item Tax Template '{template_full_name}' already exists")

	# Create Tax Account
	account = frappe.get_doc(
		{
			"doctype": "Account",
			"account_name": account_name,
			"parent_account": parent_account,
			"company": company,
			"root_type": "Liability",
			"account_type": "Tax",
			"tax_rate": float(tax_rate),
		}
	)
	account.insert()

	# Create Item Tax Template
	template = frappe.get_doc(
		{
			"doctype": "Item Tax Template",
			"title": template_name,
			"company": company,
			"taxes": [
				{
					"tax_type": account.name,
					"tax_rate": float(tax_rate),
				}
			],
		}
	)
	template.insert()

	return {
		"account": account.name,
		"template": template.name,
	}
