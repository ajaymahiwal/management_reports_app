// Copyright (c) 2025, kunleadenuga and contributors
// For license information, please see license.txt





frappe.provide("management_reports_app.monthly_actual_vs_budget");



management_reports_app.monthly_actual_vs_budget = {
	filters: get_filters(),
	baseData: null,
	// formatter: function (value, row, column, data, default_formatter, filter) {
	// 	if (
	// 		frappe.query_report.get_filter_value("selected_view") == "Growth" &&
	// 		data &&
	// 		column.colIndex >= 3
	// 	) {
	// 		const growthPercent = data[column.fieldname];

	// 		if (growthPercent == undefined) return "NA"; //making this not applicable for undefined/null values

	// 		if (column.fieldname === "total") {
	// 			value = $(`<span>${growthPercent}</span>`);
	// 		} else {
	// 			value = $(`<span>${(growthPercent >= 0 ? "+" : "") + growthPercent + "%"}</span>`);

	// 			if (growthPercent < 0) {
	// 				value = $(value).addClass("text-danger");
	// 			} else {
	// 				value = $(value).addClass("text-success");
	// 			}
	// 		}
	// 		value = $(value).wrap("<p></p>").parent().html();

	// 		return value;
	// 	} else if (frappe.query_report.get_filter_value("selected_view") == "Margin" && data) {
	// 		if (column.fieldname == "account" && data.account_name == __("Income")) {
	// 			//Taking the total income from each column (for all the financial years) as the base (100%)
	// 			this.baseData = row;
	// 		}
	// 		if (column.colIndex >= 2) {
	// 			const marginPercent = data[column.fieldname];

	// 			if (marginPercent == undefined) return "NA"; //making this not applicable for undefined/null values

	// 			value = $(`<span>${marginPercent + "%"}</span>`);
	// 			if (marginPercent < 0) value = $(value).addClass("text-danger");
	// 			else value = $(value).addClass("text-success");
	// 			value = $(value).wrap("<p></p>").parent().html();
	// 			return value;
	// 		}
	// 	}

	// 	if (data && column.fieldname == "account") {
	// 		// first column
	// 		value = data.section_name || data.account_name || value;

	// 		if (filter && filter?.text && filter?.type == "contains") {
	// 			if (!value.toLowerCase().includes(filter.text)) {
	// 				return value;
	// 			}
	// 		}

	// 		if (data.account || data.accounts) {
	// 			column.link_onclick =
	// 				"erpnext.financial_statements.open_general_ledger(" + JSON.stringify(data) + ")";
	// 		}
	// 		column.is_tree = true;
	// 	}

	// 	value = default_formatter(value, row, column, data);

	// 	if (data && !data.parent_account && !data.parent_section) {
	// 		value = $(`<span>${value}</span>`);

	// 		var $value = $(value).css("font-weight", "bold");
	// 		if (data.warn_if_negative && data[column.fieldname] < 0) {
	// 			$value.addClass("text-danger");
	// 		}

	// 		value = $value.wrap("<p></p>").parent().html();
	// 	}

	// 	return value;
	// },
	
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
                
                // Color coding for positive/negative values
                // if (!isNaN(numericValue)) {
                //     if (numericValue < 0) {
                //         style.color = '#dc3545';  // Red for negative values
                //     } else if (numericValue > 0) {
                //         style.color = '#28a745';  // Green for positive values
                //     }
                // }
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

            if (highlightAccountsWithPrimary.includes(data.account_name)) {
                style.color = 'rgb(250, 234, 4)';
                style.backgroundColor = 'rgb(0, 0, 0)';  // Light blue background
                style.borderBottom = '1px solid rgb(241, 245, 182)';
                style.fontWeight = 'bold';
            }

			if(column.fieldname == 'empty_column'){
				style.backgroundColor = '#faea04';  // Light gray background
				style.height = '45px';
			}


            if (profitAndLossAccounts.includes(data.account)) {
                if (column.fieldname && column.fieldname.includes('account')) {
                    style.backgroundColor = '#f8f9fa';  // Light gray background
                    style.fontSize = '16px';
                    style.padding = '0px';
                    style.height = '40px';
                }else{
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
		// {
		// 	fieldname: "finance_book",
		// 	label: __("Finance Book"),
		// 	fieldtype: "Link",
		// 	options: "Finance Book",
		// },
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
		// {
		// 	fieldname: "cost_center",
		// 	label: __("Cost Center"),
		// 	fieldtype: "MultiSelectList",
		// 	get_data: function (txt) {
		// 		return frappe.db.get_link_options("Cost Center", txt, {
		// 			company: frappe.query_report.get_filter_value("company"),
		// 		});
		// 	},
		// },
		// {
		// 	fieldname: "project",
		// 	label: __("Project"),
		// 	fieldtype: "MultiSelectList",
		// 	get_data: function (txt) {
		// 		return frappe.db.get_link_options("Project", txt, {
		// 			company: frappe.query_report.get_filter_value("company"),
		// 		});
		// 	},
		// },
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


frappe.query_reports["Monthly Actual Vs Budget (Other Revenue)"] = $.extend({}, management_reports_app.monthly_actual_vs_budget);



// frappe.query_reports["Monthly Actual Vs Budget (Other Revenue)"]["filters"].push({
// 	fieldname: "accumulated_values",
// 	label: __("Accumulated Values"),
// 	fieldtype: "Check",
// 	default: 1,
// });

// frappe.query_reports["Monthly Actual Vs Budget (Other Revenue)"]["filters"].push({
// 	fieldname: "include_default_book_entries",
// 	label: __("Include Default FB Entries"),
// 	fieldtype: "Check",
// 	default: 1,
// });

