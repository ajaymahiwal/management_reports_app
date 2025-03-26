# Copyright (c) 2025, kunleadenuga and contributors
# For license information, please see license.txt

import datetime
import frappe
from frappe import _
from frappe.utils import flt, formatdate, getdate
from erpnext.controllers.trends import get_period_date_ranges, get_period_month_ranges

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns(filters)
    period_month_ranges = get_period_month_ranges(filters["period"], filters["from_fiscal_year"])
    
    # Get budget data grouped by item group
    budget_data = get_budget_data(filters)
    
    # Get actual sales data grouped by item group
    actual_data = get_actual_sales_data(filters)
    
    # Combine and format data
    data = prepare_data(budget_data, actual_data, filters, period_month_ranges)
    
    chart = get_chart_data(filters, columns, data)
    

    return columns, data, None, chart

def get_budget_data(filters):
    """Get Volume Budget data grouped by item group with proper fiscal year handling"""
    return frappe.db.sql("""
        SELECT 
            bi.item_group,
            SUM(bi.budget_qty) as budget_qty,
            vb.monthly_distribution,
            vb.fiscal_year
        FROM 
            `tabVolume Budget` vb
            INNER JOIN `tabBudget Item` bi ON bi.parent = vb.name
        WHERE 
            vb.docstatus = 1
            AND vb.fiscal_year between %s and %s
            AND vb.company = %s
            AND vb.budget_against = %s
        GROUP BY 
            bi.item_group, vb.fiscal_year, vb.monthly_distribution
    """, (filters.from_fiscal_year, filters.to_fiscal_year, filters.company, filters.budget_against), as_dict=1)



def get_actual_sales_data(filters):
    """Get actual sales data from Sales Invoice grouped by item group"""
    fiscal_year_dates = get_fiscal_year_dates(filters)
    
    return frappe.db.sql("""
        SELECT 
            si.item_group,
            SUM(si.qty) as qty,
            MONTHNAME(s.posting_date) as month_name,
            YEAR(s.posting_date) as year
        FROM 
            `tabSales Invoice Item` si
            INNER JOIN `tabSales Invoice` s ON s.name = si.parent
        WHERE 
            s.docstatus = 1
            AND s.posting_date between %s and %s
            AND s.company = %s
        GROUP BY 
            si.item_group, 
            YEAR(s.posting_date),
            MONTH(s.posting_date)
    """, (fiscal_year_dates[0], fiscal_year_dates[1], filters.company), as_dict=1)

def get_fiscal_year_dates(filters):
    """Get start and end dates for the fiscal year range"""
    start_date = frappe.db.get_value("Fiscal Year", filters.from_fiscal_year, "year_start_date")
    end_date = frappe.db.get_value("Fiscal Year", filters.to_fiscal_year, "year_end_date")
    return start_date, end_date

def prepare_data(budget_data, actual_data, filters, period_month_ranges):
    """Prepare final data combining budget and actual figures"""
    data = []
    
    # Create a map of budget data by item group and fiscal year
    budget_map = {}
    for d in budget_data:
        budget_map.setdefault(d.item_group, {}).setdefault(d.fiscal_year, {
            'budget': d.budget_qty,
            'monthly_distribution': d.monthly_distribution
        })
    
    # Create a map of actual data by item group and month
    actual_map = {}
    for d in actual_data:
        key = (d.item_group, d.month_name, d.year)
        actual_map[key] = d.qty
    
    # Combine data for each item group
    processed_groups = set()
    
    # First process groups with budget
    for budget_entry in budget_data:
        if budget_entry.item_group in processed_groups:
            continue
            
        row = prepare_row(
            budget_entry.item_group,
            budget_map.get(budget_entry.item_group, {}),
            actual_map,
            filters,
            period_month_ranges
        )
        data.append(row)
        processed_groups.add(budget_entry.item_group)
    
    # Then process groups with only actuals
    for actual_entry in actual_data:
        if actual_entry.item_group in processed_groups:
            continue
            
        row = prepare_row(
            actual_entry.item_group,
            budget_map.get(actual_entry.item_group, {}),
            actual_map,
            filters,
            period_month_ranges
        )
        data.append(row)
        processed_groups.add(actual_entry.item_group)
    
    return data
def prepare_row(item_group, budget_data, actual_map, filters, period_month_ranges):
    """Prepare a single row of data"""
    row = [item_group]
    total_budget = 0
    total_actual = 0
    
    fiscal_years = get_fiscal_years(filters)
    
    for year in fiscal_years:
        year_start_date = frappe.db.get_value("Fiscal Year", year[0], "year_start_date")
        year_budget_data = budget_data.get(year[0], {})
        
        for relevant_months in period_month_ranges:
            period_budget = 0
            period_actual = 0
            
            # Calculate budget for period - only if we have budget for this specific fiscal year
            if year_budget_data.get('budget'):
                if filters["period"] == "Yearly":
                    period_budget = flt(year_budget_data.get('budget'))
                else:
                    # Distribute budget monthly/quarterly based on monthly distribution if available
                    distribution = get_monthly_distribution(year_budget_data.get('monthly_distribution'))
                    period_total_distribution = sum(distribution.get(month, 8.33) for month in relevant_months)
                    period_budget = flt(year_budget_data.get('budget')) * period_total_distribution / 100
            
            # Calculate actual for period
            for month in relevant_months:
                actual_key = (item_group, month, getdate(year_start_date).year)
                period_actual += flt(actual_map.get(actual_key, 0))
            
            # Calculate achievement percentage
            # achievement = ((period_actual - period_budget) / period_actual * 100) if period_actual != 0 else 0
            achievement = ((period_actual / period_budget) * 100) if period_budget != 0 else 0
            
            row.extend([period_budget, period_actual, achievement])
            total_budget += period_budget
            total_actual += period_actual
    
    if filters["period"] != "Yearly":
        # total_achievement = ((total_actual - total_budget) / total_actual * 100) if total_actual != 0 else 0
        total_achievement = ((total_actual / total_budget) * 100) if  total_budget != 0 else 0

        row.extend([total_budget, total_actual, total_achievement])
    
    return row


def get_monthly_distribution(distribution_id):
    """Get monthly distribution percentages"""
    if not distribution_id:
        return {}
        
    distribution = {}
    dist_data = frappe.get_all(
        "Monthly Distribution Percentage",
        filters={"parent": distribution_id},
        fields=["month", "percentage_allocation"]
    )
    
    for d in dist_data:
        distribution[d.month] = flt(d.percentage_allocation)
    
    return distribution


def get_columns(filters):
    columns = [
        {
            "label": _("Item Group"),
            "fieldname": "item_group",
            "fieldtype": "Link",
            "options": "Item Group",
            "width": 150
        }
    ]

    group_months = False if filters["period"] == "Monthly" else True
    fiscal_year = get_fiscal_years(filters)

    for year in fiscal_year:
        for from_date, to_date in get_period_date_ranges(filters["period"], year[0]):
            if filters["period"] == "Yearly":
                # For Yearly, add simple year-based columns
                columns.extend([
                    {
                        "label": _("Budget") + " " + str(year[0]),
                        "fieldtype": "Float",
                        "fieldname": f"budget_{year[0]}",
                        "width": 150
                    },
                    {
                        "label": _("Actual") + " " + str(year[0]),
                        "fieldtype": "Float",
                        "fieldname": f"actual_{year[0]}",
                        "width": 150
                    },
                    {
                        "label": _("% Ach") + " " + str(year[0]),
                        "fieldtype": "Percent",
                        "fieldname": f"achievement_{year[0]}",
                        "width": 150
                    }
                ])
            else:
                # For Monthly/Quarterly/Half-Yearly
                if group_months:
                    period_label = formatdate(from_date, format_string="MMM") + "-" + formatdate(to_date, format_string="MMM")
                else:
                    period_label = formatdate(from_date, format_string="MMM")
                
                columns.extend([
                    {
                        "label": _("Budget") + " (" + period_label + ") " + str(year[0]),
                        "fieldtype": "Float",
                        "fieldname": f"budget_{period_label}_{year[0]}".lower().replace("-", "_"),
                        "width": 150
                    },
                    {
                        "label": _("Actual") + " (" + period_label + ") " + str(year[0]),
                        "fieldtype": "Float",
                        "fieldname": f"actual_{period_label}_{year[0]}".lower().replace("-", "_"),
                        "width": 150
                    },
                    {
                        "label": _("% Ach") + " (" + period_label + ") " + str(year[0]),
                        "fieldtype": "Percent",
                        "fieldname": f"achievement_{period_label}_{year[0]}".lower().replace("-", "_"),
                        "width": 150
                    }
                ])

    # Add total columns if not yearly
    if filters["period"] != "Yearly":
        columns.extend([
            {
                "label": _("Total Budget"),
                "fieldtype": "Float",
                "fieldname": "total_budget",
                "width": 150
            },
            {
                "label": _("Total Actual"),
                "fieldtype": "Float",
                "fieldname": "total_actual",
                "width": 150
            },
            {
                "label": _("Total % Ach"),
                "fieldtype": "Percent",
                "fieldname": "total_achievement",
                "width": 150
            }
        ])

    return columns

def get_fiscal_years(filters):
    return frappe.db.sql("""
        select name
        from `tabFiscal Year`
        where name between %(from_fiscal_year)s and %(to_fiscal_year)s
    """, {
        "from_fiscal_year": filters["from_fiscal_year"],
        "to_fiscal_year": filters["to_fiscal_year"]
    })

def get_chart_data(filters, columns, data):
    if not data:
        return None

    labels = []
    fiscal_year = get_fiscal_years(filters)
    group_months = False if filters["period"] == "Monthly" else True

    for year in fiscal_year:
        for from_date, to_date in get_period_date_ranges(filters["period"], year[0]):
            if filters["period"] == "Yearly":
                labels.append(str(year[0]))
            else:
                if group_months:
                    label = (
                        formatdate(from_date, format_string="MMM")
                        + "-"
                        + formatdate(to_date, format_string="MMM")
                    )
                    labels.append(label)
                else:
                    label = formatdate(from_date, format_string="MMM")
                    labels.append(label)

    no_of_columns = len(labels)
    budget_values = []
    actual_values = []

    for row in data:
        values = row[1:]  # Skip first column (Item Group)
        for i in range(0, len(values), 2):
            if i//2 < no_of_columns:  # Only take values for the current period
                budget_values.append(values[i])
                actual_values.append(values[i+1])

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": _("Budget"), "values": budget_values, "chartType": "bar"},
                {"name": _("Actual Sales"), "values": actual_values, "chartType": "bar"}
            ]
        },
        "type": "bar"
    }
