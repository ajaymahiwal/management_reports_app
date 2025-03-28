// Copyright (c) 2025, kunleadenuga and contributors
// For license information, please see license.txt



frappe.provide("management_reports_app.productive_report");



management_reports_app.productive_report = {
	filters: get_filters(),
	baseData: null,
	formatter: function (value, row, column, data, default_formatter) {
		// First apply the default formatting
		value = default_formatter(value, row, column, data);
	  
		// Base styling for all cells
		let style = {
			display: 'block',
			padding: '2px 5px',
			fontWeight: '600'
		};
	  
		// Column-specific styling
		if (column.fieldname) {
			// Style for the account name column
			if (column.fieldname === 'account') {
				style.minWidth = '400px';  // Wider column for account names
				style.backgroundColor = '#f8f9fa';  // Light gray background
			}
			// Style for decimal/value columns
			else if (column.fieldname.includes('dec')) {
				style.textAlign = 'right';
				style.backgroundColor = '#f8f9fa';  // Light gray background
				
				// Parse the numeric value
				const numericValue = parseFloat(String(value).replace(/[^\d.-]/g, ''));
			}
		}
	  
		// Special styling for specific accounts
		if (data && data.account_name) {
			const highlightAccountsWithPrimary = [
				"Gross Profit",
				"EBIT",
				"EBITDA",
				"Operating Expense",
				"Profit Before Tax"
			];
			
			const profitAndLossAccounts = [
				"Profit for the year"
			];
			
			// // Add margin accounts that should be displayed as percentages
			// const percentageAccounts = [
			// 	"EBITDA Margin",
			// 	"COS Margin",
			// 	"HR Margin",
			// 	"Admin Cost Margin"
			// ];
			
			// // Format percentage accounts
			// if (percentageAccounts.includes(data.account_name) && column.fieldtype === "Currency" && value !== "") {
			// 	// Parse the numeric value
			// 	const numericValue = parseFloat(String(value).replace(/[^\d.-]/g, ''));
			// 	if (!isNaN(numericValue)) {
			// 		// Format as percentage with 2 decimal places
			// 		value = numericValue.toFixed(2) + '%';
			// 	}
			// }
			
			// Handle Appointment Generation & Marketing
			if (data && data.account_name) {
				const percentageAccounts = [
					"EBITDA Margin",
					"COS Margin", 
					"HR Margin", 
					"Admin Cost Margin",
					"Appointment Generation & Marketing",
				];
				
				if (percentageAccounts.includes(data.account_name)) {
					if (column.fieldname !== 'account' && column.fieldname !== 'account_name') {
						let numericValue = parseFloat(String(value).replace(/[^\d.-]/g, ''));
						if (!isNaN(numericValue)) {
							value = numericValue.toFixed(2) + '%';
						}
					}
				}
				
			}
			
			if (highlightAccountsWithPrimary.includes(data.account_name)) {
				style.color = 'rgb(250, 234, 4)';
				style.backgroundColor = 'rgb(0, 0, 0)';  // Black background
				style.borderBottom = '1px solid rgb(241, 245, 182)';
				style.fontWeight = 'bold';
			}
			
			if(column.fieldname == 'empty_column'){
				style.backgroundColor = '#faea04';  // Yellow background
				style.height = '45px';
			}
			
			if (profitAndLossAccounts.includes(data.account)) {
				if (column.fieldname && column.fieldname.includes('account')) {
					style.backgroundColor = '#f8f9fa';  // Light gray background
					style.fontSize = '16px';
					style.padding = '0px';
					style.height = '40px';
				} else {
					const numericValue = parseFloat(String(data[column.fieldname]).replace(/[^\d.-]/g, ''));
					style.color = numericValue >= 0 ? '#1cb408' : '#eb1f1f';
					style.backgroundColor = numericValue >= 0 ? '#e8f5e9' : '#ffebee';
					style.fontWeight = 'bold';
				}
			}
		}
	  
		// Convert style object to inline CSS string
		const styleString = Object.entries(style)
			.map(([key, value]) => `${key.replace(/([A-Z])/g, '-$1').toLowerCase()}: ${value}`)
			.join('; ');
	  
		return `<span style="${styleString}">${value}</span>`;
	},
	open_general_ledger: function (data) {
		if (!data.account && !data.accounts) return;
		let project = $.grep(frappe.query_report.filters, function (e) {
			return e.df.fieldname == "project";
		});

		frappe.route_options = {
			account: data.account || data.accounts,
			company: frappe.query_report.get_filter_value("company"),
			from_date: data.from_date || data.year_start_date,
			to_date: data.to_date || data.year_end_date,
			project: project && project.length > 0 ? project[0].$input.val() : "",
		};

		let report = "General Ledger";

		if (["Payable", "Receivable"].includes(data.account_type)) {
			report = data.account_type == "Payable" ? "Accounts Payable" : "Accounts Receivable";
			frappe.route_options["party_account"] = data.account;
			frappe.route_options["report_date"] = data.year_end_date;
		}

		frappe.set_route("query-report", report);
	},
	tree: true,
	name_field: "account",
	parent_field: "parent_account",
	initial_depth: 3,
	onload: function (report) {
		// dropdown for links to other financial statements
		erpnext.financial_statements.filters = get_filters();

		let fiscal_year = erpnext.utils.get_fiscal_year(frappe.datetime.get_today());
		var filters = report.get_values();

		if (!filters.period_start_date || !filters.period_end_date) {
			frappe.model.with_doc("Fiscal Year", fiscal_year, function (r) {
				var fy = frappe.model.get_doc("Fiscal Year", fiscal_year);
				frappe.query_report.set_filter_value({
					period_start_date: fy.year_start_date,
					period_end_date: fy.year_end_date,
				});
			});
		}

		if (report.page) {
			const views_menu = report.page.add_custom_button_group(__("Financial Statements"));

			report.page.add_custom_menu_item(views_menu, __("Balance Sheet"), function () {
				var filters = report.get_values();
				frappe.set_route("query-report", "Balance Sheet", { company: filters.company });
			});

			report.page.add_custom_menu_item(views_menu, __("Profit and Loss"), function () {
				var filters = report.get_values();
				frappe.set_route("query-report", "Profit and Loss Statement", { company: filters.company });
			});

			report.page.add_custom_menu_item(views_menu, __("Cash Flow Statement"), function () {
				var filters = report.get_values();
				frappe.set_route("query-report", "Cash Flow", { company: filters.company });
			});
		}
	},
};

function get_filters() {
	let filters = [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "filter_based_on",
			label: __("Filter Based On"),
			fieldtype: "Select",
			options: ["Fiscal Year"],
			// options: ["Fiscal Year", "Date Range"],
			default: ["Fiscal Year"],
			reqd: 1,
			on_change: function () {
				let filter_based_on = frappe.query_report.get_filter_value("filter_based_on");
				frappe.query_report.toggle_filter_display(
					"from_fiscal_year",
					filter_based_on === "Date Range"
				);
				frappe.query_report.toggle_filter_display("to_fiscal_year", filter_based_on === "Date Range");
				frappe.query_report.toggle_filter_display(
					"period_start_date",
					filter_based_on === "Fiscal Year"
				);
				frappe.query_report.toggle_filter_display(
					"period_end_date",
					filter_based_on === "Fiscal Year"
				);

				frappe.query_report.refresh();
			},
		},
		{
			fieldname: "period_start_date",
			label: __("Start Date"),
			fieldtype: "Date",
			reqd: 1,
			depends_on: "eval:doc.filter_based_on == 'Date Range'",
		},
		{
			fieldname: "period_end_date",
			label: __("End Date"),
			fieldtype: "Date",
			reqd: 1,
			depends_on: "eval:doc.filter_based_on == 'Date Range'",
		},
		{
			fieldname: "from_fiscal_year",
			label: __("Start Year"),
			fieldtype: "Link",
			options: "Fiscal Year",
			reqd: 1,
			depends_on: "eval:doc.filter_based_on == 'Fiscal Year'",
		},
		{
			fieldname: "to_fiscal_year",
			label: __("End Year"),
			fieldtype: "Link",
			options: "Fiscal Year",
			reqd: 1,
			depends_on: "eval:doc.filter_based_on == 'Fiscal Year'",
		},
		{
			fieldname: "periodicity",
			label: __("Periodicity"),
			fieldtype: "Select",
			options: [
				{ value: "Monthly", label: __("Monthly") },
				// { value: "Quarterly", label: __("Quarterly") },
				// { value: "Half-Yearly", label: __("Half-Yearly") },
				// { value: "Yearly", label: __("Yearly") },
			],
			default: "Monthly",
			reqd: 1,
		},
		// Note:
		// If you are modifying this array such that the presentation_currency object
		// is no longer the last object, please make adjustments in cash_flow.js
		// accordingly.
		{
			fieldname: "presentation_currency",
			label: __("Currency"),
			fieldtype: "Select",
			options: erpnext.get_presentation_currency_list(),
		},
	];

	// Dynamically set 'default' values for fiscal year filters
	let fy_filters = filters.filter((x) => {
		return ["from_fiscal_year", "to_fiscal_year"].includes(x.fieldname);
	});
	let fiscal_year = erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), false, true);
	if (fiscal_year) {
		let fy = erpnext.utils.get_fiscal_year(frappe.datetime.get_today(), false, false);
		fy_filters.forEach((x) => {
			x.default = fy;
		});
	}

	return filters;
}


frappe.query_reports["Productive Report"] = $.extend({}, management_reports_app.productive_report);


