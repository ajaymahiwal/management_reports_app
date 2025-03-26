// Copyright (c) 2025, kunleadenuga and contributors
// For license information, please see license.txt


frappe.query_reports["Profit and Loss Summary Statement"] = $.extend({}, erpnext.financial_statements, {
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
                style.color = 'rgb(45, 180, 233)';
                style.backgroundColor = '#e3f2fd';  // Light blue background
                style.borderBottom = '1px solid #90caf9';
                style.fontWeight = 'bold';
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
    }
});

erpnext.utils.add_dimensions("Profit and Loss Summary Statement", 10);

// frappe.query_reports["Profit and Loss Summary Statement"]["filters"].push({
// 	fieldname: "selected_view",
// 	label: __("Select View"),
// 	fieldtype: "Select",
// 	options: [
// 		{ value: "Report", label: __("Report View") },
// 		// { value: "Growth", label: __("Growth View") },
// 		// { value: "Margin", label: __("Margin View") },
// 	],
// 	default: "Report",
// 	reqd: 1,
// });

frappe.query_reports["Profit and Loss Summary Statement"]["filters"].push({
	fieldname: "accumulated_values",
	label: __("Accumulated Values"),
	fieldtype: "Check",
	default: 1,
});

frappe.query_reports["Profit and Loss Summary Statement"]["filters"].push({
	fieldname: "include_default_book_entries",
	label: __("Include Default FB Entries"),
	fieldtype: "Check",
	default: 1,
});
