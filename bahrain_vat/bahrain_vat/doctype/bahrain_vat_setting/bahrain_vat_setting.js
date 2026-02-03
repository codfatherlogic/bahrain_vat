// Copyright (c) 2024, sammish and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bahrain VAT Setting", {
	refresh(frm) {
		// Auto-load template for new documents
		if (frm.is_new() && frm.doc.bahrain_vat_sales_accounts.length === 0) {
			load_template_locally(frm);
		}

		// Add button to reload template for existing documents
		if (!frm.is_new()) {
			frm.add_custom_button(__("Load Standard Template"), function () {
				frappe.confirm(
					__("This will replace all existing entries with the standard Bahrain VAT template. Continue?"),
					function () {
						frappe.call({
							method: "bahrain_vat.bahrain_vat.doctype.bahrain_vat_setting.bahrain_vat_setting.load_standard_template",
							args: {
								docname: frm.doc.name,
							},
							callback: function (r) {
								if (r.message) {
									frappe.msgprint(r.message.message);
									frm.reload_doc();
								}
							},
						});
					}
				);
			});
		}

		// Add button to create Tax Account and Item Tax Template
		frm.add_custom_button(
			__("Create Tax Account & Template"),
			function () {
				show_create_tax_dialog(frm);
			},
			__("Setup")
		);

		// Filter accounts by company
		frm.set_query("account", "bahrain_vat_sales_accounts", function () {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0,
				},
			};
		});

		frm.set_query("account", "bahrain_vat_purchase_accounts", function () {
			return {
				filters: {
					company: frm.doc.company,
					is_group: 0,
				},
			};
		});
	},
});

function show_create_tax_dialog(frm) {
	if (!frm.doc.company) {
		frappe.msgprint(__("Please select a Company first"));
		return;
	}

	let d = new frappe.ui.Dialog({
		title: __("Create Tax Account & Item Tax Template"),
		fields: [
			{
				label: __("Tax Rate (%)"),
				fieldname: "tax_rate",
				fieldtype: "Select",
				options: ["5", "10"],
				reqd: 1,
				default: "10",
			},
			{
				label: __("Account Name"),
				fieldname: "account_name",
				fieldtype: "Data",
				reqd: 1,
				default: "VAT 10%",
				depends_on: "eval:doc.tax_rate",
				onchange: function () {},
			},
			{
				label: __("Parent Account"),
				fieldname: "parent_account",
				fieldtype: "Link",
				options: "Account",
				reqd: 1,
				get_query: function () {
					return {
						filters: {
							company: frm.doc.company,
							is_group: 1,
							root_type: "Liability",
						},
					};
				},
			},
			{
				fieldtype: "Section Break",
			},
			{
				label: __("Item Tax Template Name"),
				fieldname: "template_name",
				fieldtype: "Data",
				reqd: 1,
				default: "VAT 10%",
			},
		],
		primary_action_label: __("Create"),
		primary_action(values) {
			frappe.call({
				method: "bahrain_vat.bahrain_vat.doctype.bahrain_vat_setting.bahrain_vat_setting.create_tax_account_and_template",
				args: {
					company: frm.doc.company,
					tax_rate: values.tax_rate,
					account_name: values.account_name,
					parent_account: values.parent_account,
					template_name: values.template_name,
				},
				callback: function (r) {
					if (r.message) {
						frappe.msgprint({
							title: __("Success"),
							indicator: "green",
							message: __(
								"Created:<br>• Account: {0}<br>• Item Tax Template: {1}",
								[r.message.account, r.message.template]
							),
						});
						d.hide();
						frm.reload_doc();
					}
				},
			});
		},
	});

	// Update default names based on tax rate selection
	d.fields_dict.tax_rate.$input.on("change", function () {
		let rate = d.get_value("tax_rate");
		d.set_value("account_name", `VAT ${rate}%`);
		d.set_value("template_name", `VAT ${rate}%`);
	});

	d.show();
}

function load_template_locally(frm) {
	// VAT on Sales template (Boxes 1-6)
	const sales_template = [
		{ box_number: "1(a)", title: "Standard rated sales at 5%" },
		{ box_number: "1(b)", title: "Standard rated sales at 10%" },
		{ box_number: "2", title: "Sales to registered taxpayers in other GCC States" },
		{ box_number: "3", title: "Sales subject to domestic reverse charge mechanism" },
		{ box_number: "4", title: "Zero rated domestic sales" },
		{ box_number: "5", title: "Exports" },
		{ box_number: "6", title: "Exempt sales" },
	];

	// VAT on Purchases template (Boxes 8-13)
	const purchase_template = [
		{ box_number: "8(a)", title: "Standard rated domestic purchases at 5%" },
		{ box_number: "8(b)", title: "Standard rated domestic purchases at 10%" },
		{ box_number: "9", title: "Imports subject to VAT paid at customs" },
		{ box_number: "10", title: "Imports subject to VAT deferral at customs" },
		{ box_number: "11(a)", title: "Imports subject to VAT accounted for through reverse charge mechanism at 5%" },
		{ box_number: "11(b)", title: "Imports subject to VAT accounted for through reverse charge mechanism at 10%" },
		{ box_number: "12", title: "Purchases subject to domestic reverse charge mechanism" },
		{ box_number: "13", title: "Purchases from non-registered suppliers, zero-rated/exempt purchases" },
	];

	// Clear and add sales accounts
	frm.clear_table("bahrain_vat_sales_accounts");
	sales_template.forEach(function (item) {
		let row = frm.add_child("bahrain_vat_sales_accounts");
		row.box_number = item.box_number;
		row.title = item.title;
	});

	// Clear and add purchase accounts
	frm.clear_table("bahrain_vat_purchase_accounts");
	purchase_template.forEach(function (item) {
		let row = frm.add_child("bahrain_vat_purchase_accounts");
		row.box_number = item.box_number;
		row.title = item.title;
	});

	frm.refresh_field("bahrain_vat_sales_accounts");
	frm.refresh_field("bahrain_vat_purchase_accounts");
}
