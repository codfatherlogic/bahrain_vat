// Copyright (c) 2024, sammish and contributors
// For license information, please see license.txt

frappe.query_reports["Bahrain VAT"] = {
	onload() {
		frappe.breadcrumbs.add("Accounts");
	},
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			reqd: 1,
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.get_today(),
		},
	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (!data) return value;

		// Style header rows (VAT on Sales, VAT on Purchases, Net VAT due)
		if (data.is_header) {
			value = $(`<span>${value}</span>`);
			value.css({
				"font-weight": "bold",
				"background-color": "#f5f5f5",
			});
			value = value.wrap("<div></div>").parent().html();
		}

		// Style total rows (Total sales, Total purchases, Total VAT due)
		if (data.is_total) {
			value = $(`<span>${value}</span>`);
			value.css({
				"font-weight": "bold",
			});
			value = value.wrap("<div></div>").parent().html();
		}

		return value;
	},
};
