# Copyright (c) 2024, sammish and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import get_url_to_list


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"fieldname": "box_number",
			"label": _("Box#"),
			"fieldtype": "Data",
			"width": 80,
		},
		{
			"fieldname": "description",
			"label": _("Description"),
			"fieldtype": "Data",
			"width": 450,
		},
		{
			"fieldname": "amount",
			"label": _("Amount"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150,
		},
		{
			"fieldname": "adjustment",
			"label": _("Adjustment"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150,
		},
		{
			"fieldname": "vat_amount",
			"label": _("VAT Amount"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150,
		},
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Currency",
			"width": 150,
			"hidden": 1,
		},
	]


def get_data(filters):
	data = []

	# Validate if vat settings exist
	company = filters.get("company")
	company_currency = frappe.get_cached_value("Company", company, "default_currency")

	if frappe.db.exists("Bahrain VAT Setting", company) is None:
		url = get_url_to_list("Bahrain VAT Setting")
		frappe.msgprint(_('Create <a href="{}">Bahrain VAT Setting</a> for this company').format(url))
		return data

	bahrain_vat_setting = frappe.get_doc("Bahrain VAT Setting", company)

	# ========== VAT on Sales Section ==========
	append_data(data, "", "<b>VAT on Sales</b>", "", "", "", company_currency, is_header=True)

	sales_total_amount = 0
	sales_total_adjustment = 0
	sales_total_vat = 0

	for vat_setting in bahrain_vat_setting.bahrain_vat_sales_accounts:
		amount, adjustment, vat = get_tax_data_for_each_vat_setting(vat_setting, filters, "Sales Invoice")

		append_data(
			data,
			vat_setting.box_number or "",
			vat_setting.title or "",
			amount,
			adjustment,
			vat,
			company_currency,
		)

		sales_total_amount += amount
		sales_total_adjustment += adjustment
		sales_total_vat += vat

	# Total sales row (Box 7)
	append_data(
		data,
		"7",
		"<b>Total sales</b>",
		sales_total_amount,
		sales_total_adjustment,
		sales_total_vat,
		company_currency,
		is_total=True,
	)

	# Empty row separator
	append_data(data, "", "", "", "", "", company_currency)

	# ========== VAT on Purchases Section ==========
	append_data(data, "", "<b>VAT on Purchases</b>", "", "", "", company_currency, is_header=True)

	purchase_total_amount = 0
	purchase_total_adjustment = 0
	purchase_total_vat = 0

	for vat_setting in bahrain_vat_setting.bahrain_vat_purchase_accounts:
		amount, adjustment, vat = get_tax_data_for_each_vat_setting(vat_setting, filters, "Purchase Invoice")

		append_data(
			data,
			vat_setting.box_number or "",
			vat_setting.title or "",
			amount,
			adjustment,
			vat,
			company_currency,
		)

		purchase_total_amount += amount
		purchase_total_adjustment += adjustment
		purchase_total_vat += vat

	# Total purchases row (Box 14)
	append_data(
		data,
		"14",
		"<b>Total purchases</b>",
		purchase_total_amount,
		purchase_total_adjustment,
		purchase_total_vat,
		company_currency,
		is_total=True,
	)

	# Empty row separator
	append_data(data, "", "", "", "", "", company_currency)

	# ========== Net VAT due Section ==========
	append_data(data, "", "<b>Net VAT due</b>", "", "", "", company_currency, is_header=True)

	# Calculate Net VAT (Box 15)
	net_vat = sales_total_vat - purchase_total_vat

	append_data(
		data,
		"15",
		"<b>Total VAT due for current period</b>",
		"",
		"",
		net_vat,
		company_currency,
		is_total=True,
	)

	return data


def get_tax_data_for_each_vat_setting(vat_setting, filters, doctype):
	"""Get tax data for a specific VAT setting entry.

	The taxable Amount and the VAT must be scoped the *same* way, otherwise the
	two columns disagree (e.g. Amount computed from item tax templates while VAT
	is read from the invoice-level tax account).

	- When a VAT account is configured, the box is defined by that account. The
	  taxable base is the net of items on invoices that posted tax to the
	  account, and the VAT is the tax posted to it. Items explicitly tagged to a
	  *different* item tax template are excluded; items with no template are
	  included (they are taxed at the invoice's rate). This keeps
	  base x rate == VAT and reconciles with the Sales Register.
	- When only an item tax template is configured (e.g. zero-rated / exempt
	  boxes that have no VAT account), the base is the net of items carrying that
	  template and the VAT is zero.
	"""
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	company = filters.get("company")

	total_amount = 0
	total_adjustment = 0
	total_vat = 0

	# Skip if no item_tax_template and no account configured
	if not vat_setting.item_tax_template and not vat_setting.account:
		return total_amount, total_adjustment, total_vat

	invoices = frappe.get_all(
		doctype,
		filters={
			"docstatus": 1,
			"posting_date": ["between", [from_date, to_date]],
			"company": company,
		},
		fields=["name", "is_return"],
	)

	tax_doctype = "Purchase Taxes and Charges" if doctype == "Purchase Invoice" else "Sales Taxes and Charges"

	for invoice in invoices:
		invoice_items = []

		if vat_setting.account:
			# Account-defined box: only invoices that posted tax to this account.
			has_tax_account = frappe.db.exists(
				tax_doctype,
				{"docstatus": 1, "parent": invoice.name, "account_head": vat_setting.account},
			)
			if not has_tax_account:
				continue

			all_items = frappe.get_all(
				f"{doctype} Item",
				filters={"docstatus": 1, "parent": invoice.name},
				fields=["item_code", "net_amount", "base_net_amount", "item_tax_template"],
			)
			# Include items for this rate: those matching the configured template
			# and those with no template (untagged items taxed at the invoice's
			# rate). Exclude items explicitly tagged to a different rate.
			for item in all_items:
				if (
					not vat_setting.item_tax_template
					or not item.get("item_tax_template")
					or item.get("item_tax_template") == vat_setting.item_tax_template
				):
					invoice_items.append(item)

			# VAT belongs to this box whenever the account posted tax, regardless
			# of item-template tagging.
			total_vat += get_tax_amount(vat_setting.account, doctype, invoice.name)
		else:
			# Template-only box (no VAT account, e.g. zero-rated / exempt).
			invoice_items = frappe.get_all(
				f"{doctype} Item",
				filters={
					"docstatus": 1,
					"parent": invoice.name,
					"item_tax_template": vat_setting.item_tax_template,
				},
				fields=["item_code", "net_amount", "base_net_amount"],
			)

		for item in invoice_items:
			amount = item.get("base_net_amount") or item.get("net_amount") or 0

			if invoice.is_return == 0:
				total_amount += amount
			else:
				total_adjustment += amount

	return total_amount, total_adjustment, total_vat


def append_data(data, box_number, description, amount, adjustment, vat_amount, currency, is_header=False, is_total=False):
	"""Append a row to the report data"""
	data.append({
		"box_number": box_number,
		"description": description,
		"amount": amount if amount != "" else None,
		"adjustment": adjustment if adjustment != "" else None,
		"vat_amount": vat_amount if vat_amount != "" else None,
		"currency": currency,
		"is_header": is_header,
		"is_total": is_total,
	})


def get_tax_amount(account_head, doctype, parent):
	"""Get the tax amount for a specific account and invoice"""
	if not account_head:
		return 0

	if doctype == "Sales Invoice":
		tax_doctype = "Sales Taxes and Charges"
	elif doctype == "Purchase Invoice":
		tax_doctype = "Purchase Taxes and Charges"
	else:
		return 0

	tax_entries = frappe.get_all(
		tax_doctype,
		filters={"docstatus": 1, "parent": parent, "account_head": account_head},
		fields=["tax_amount", "base_tax_amount"],
	)

	total_tax = 0
	for entry in tax_entries:
		tax = entry.get("base_tax_amount") or entry.get("tax_amount") or 0
		total_tax += tax

	return total_tax
