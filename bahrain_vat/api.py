# Copyright (c) 2024, sammish and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, get_first_day, get_last_day, nowdate


@frappe.whitelist()
def get_output_vat(company=None, from_date=None, to_date=None):
	"""Get total Output VAT (Sales) for the period"""
	if not company:
		company = frappe.defaults.get_user_default("Company")
	if not from_date:
		from_date = get_first_day(nowdate())
	if not to_date:
		to_date = get_last_day(nowdate())

	if not frappe.db.exists("Bahrain VAT Setting", company):
		return 0

	setting = frappe.get_doc("Bahrain VAT Setting", company)
	total_vat = 0

	for account_row in setting.bahrain_vat_sales_accounts:
		if account_row.account:
			vat = get_tax_amount_for_account(account_row.account, from_date, to_date, "Sales Invoice")
			total_vat += vat

	return total_vat


@frappe.whitelist()
def get_input_vat(company=None, from_date=None, to_date=None):
	"""Get total Input VAT (Purchases) for the period"""
	if not company:
		company = frappe.defaults.get_user_default("Company")
	if not from_date:
		from_date = get_first_day(nowdate())
	if not to_date:
		to_date = get_last_day(nowdate())

	if not frappe.db.exists("Bahrain VAT Setting", company):
		return 0

	setting = frappe.get_doc("Bahrain VAT Setting", company)
	total_vat = 0

	for account_row in setting.bahrain_vat_purchase_accounts:
		if account_row.account:
			vat = get_tax_amount_for_account(account_row.account, from_date, to_date, "Purchase Invoice")
			total_vat += vat

	return total_vat


@frappe.whitelist()
def get_net_vat(company=None, from_date=None, to_date=None):
	"""Get Net VAT (Output - Input) for the period - Returns format for Number Card"""
	if not company:
		company = frappe.defaults.get_user_default("Company")
	if not from_date:
		from_date = get_first_day(nowdate())
	if not to_date:
		to_date = get_last_day(nowdate())

	output_vat = get_output_vat(company, from_date, to_date)
	input_vat = get_input_vat(company, from_date, to_date)
	net_vat = output_vat - input_vat

	return {
		"value": net_vat,
		"fieldtype": "Currency",
		"route_options": {"company": company},
		"route": ["query-report", "Bahrain VAT"],
	}


def get_tax_amount_for_account(account_head, from_date, to_date, doctype):
	"""Get total tax amount for a specific account"""
	if doctype == "Sales Invoice":
		tax_doctype = "Sales Taxes and Charges"
	else:
		tax_doctype = "Purchase Taxes and Charges"

	result = frappe.db.sql(
		"""
		SELECT SUM(IFNULL(tc.base_tax_amount, tc.tax_amount)) as total_tax
		FROM `tab{tax_doctype}` tc
		INNER JOIN `tab{doctype}` inv ON tc.parent = inv.name
		WHERE tc.docstatus = 1
		AND tc.account_head = %s
		AND inv.posting_date BETWEEN %s AND %s
		""".format(tax_doctype=tax_doctype, doctype=doctype),
		(account_head, from_date, to_date),
		as_dict=True,
	)

	return result[0].total_tax or 0 if result else 0


@frappe.whitelist()
def get_vat_summary(company=None):
	"""Get VAT summary for dashboard"""
	if not company:
		company = frappe.defaults.get_user_default("Company")

	from_date = get_first_day(nowdate())
	to_date = get_last_day(nowdate())

	output_vat = get_output_vat(company, from_date, to_date)
	input_vat = get_input_vat(company, from_date, to_date)
	net_vat = output_vat - input_vat

	return {
		"output_vat": output_vat,
		"input_vat": input_vat,
		"net_vat": net_vat,
		"period": f"{from_date} to {to_date}",
	}
