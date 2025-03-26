# Copyright (c) 2025, kunleadenuga and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import flt, formatdate, getdate
from erpnext.controllers.trends import get_period_date_ranges, get_period_month_ranges

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns(filters)
    period_month_ranges = get_period_month_ranges(filters["period"], filters["from_fiscal_year"])
    
    # Get sales data grouped by item group
    sales_data = get_sales_data(filters)
    
    # Prepare final data
    data = prepare_data(sales_data, filters, period_month_ranges)
    
    chart = get_chart_data(filters, columns, data)
        

    totals = ["Total"] + [sum(row[i] for row in data) for i in range(1, len(data[0]))]

    # Append empty row (if needed)
    empty_row = [None] * len(data[0])
    data.append(empty_row)  # Optional spacing row
    data.append(totals)

    return columns, data, None, chart


def get_sales_data(filters):
    """Get sales data from Sales Invoice Item grouped by item group"""
    fiscal_year_dates = get_fiscal_year_dates(filters)
    
    return frappe.db.sql("""
        SELECT 
            si.item_group,
            SUM(si.qty) as volume,
            SUM(si.amount) as amount,
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


def prepare_data(sales_data, filters, period_month_ranges):
    """Prepare final data with period-specific contribution calculations"""
    data = []
    item_group_data = {}
    period_totals = {}  # To store totals for each period
    
    # First pass: Calculate totals and organize data by item group
    for entry in sales_data:
        if entry.item_group not in item_group_data:
            item_group_data[entry.item_group] = {
                'periods': {},
                'total_volume': 0,
                'total_amount': 0
            }
        
        period_key = (entry.year, entry.month_name)
        if period_key not in item_group_data[entry.item_group]['periods']:
            item_group_data[entry.item_group]['periods'][period_key] = {
                'volume': 0,
                'amount': 0
            }
        
        item_group_data[entry.item_group]['periods'][period_key]['volume'] += flt(entry.volume)
        item_group_data[entry.item_group]['periods'][period_key]['amount'] += flt(entry.amount)
        item_group_data[entry.item_group]['total_volume'] += flt(entry.volume)
        item_group_data[entry.item_group]['total_amount'] += flt(entry.amount)
    
    # Calculate period totals first
    fiscal_years = get_fiscal_years(filters)
    for year in fiscal_years:
        year_start_date = frappe.db.get_value("Fiscal Year", year[0], "year_start_date")
        current_year = getdate(year_start_date).year
        
        for period_months in period_month_ranges:
            period_total = 0
            for month in period_months:
                for item_group in item_group_data:
                    period_key = (current_year, month)
                    if period_key in item_group_data[item_group]['periods']:
                        period_total += flt(item_group_data[item_group]['periods'][period_key]['amount'])
            
            period_id = f"{year[0]}_{period_months[0]}_{period_months[-1]}"
            period_totals[period_id] = period_total

    # Calculate grand total for overall contribution
    grand_total = sum(group_data['total_amount'] for group_data in item_group_data.values())
    
    # Second pass: Create rows with proper period distribution and contributions
    for item_group in item_group_data:
        row = [item_group]
        group_total = 0
        
        for year in fiscal_years:
            year_start_date = frappe.db.get_value("Fiscal Year", year[0], "year_start_date")
            current_year = getdate(year_start_date).year
            
            for period_months in period_month_ranges:
                period_volume = 0
                period_amount = 0
                
                # Sum up the values for all months in the period
                for month in period_months:
                    period_key = (current_year, month)
                    if period_key in item_group_data[item_group]['periods']:
                        period_data = item_group_data[item_group]['periods'][period_key]
                        period_volume += flt(period_data['volume'])
                        period_amount += flt(period_data['amount'])
                
                # Calculate period-specific contribution
                period_id = f"{year[0]}_{period_months[0]}_{period_months[-1]}"
                period_contribution = (period_amount / period_totals[period_id] * 100) if period_totals[period_id] else 0
                
                row.extend([period_volume, period_amount, period_contribution])
                group_total += period_amount
        
        if filters["period"] != "Yearly":
            # Calculate total contribution based on grand total
            total_contribution = (group_total / grand_total * 100) if grand_total else 0
            row.extend([
                item_group_data[item_group]['total_volume'],
                group_total,
                total_contribution
            ])
        
        data.append(row)
    
    # Sort data by total amount in descending order
    if filters["period"] != "Yearly":
        data.sort(key=lambda x: x[-2], reverse=True)
    else:
        data.sort(key=lambda x: sum(x[i] for i in range(2, len(x), 3)), reverse=True)
    
    return data


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
                period_label = str(year[0])
            else:
                if group_months:
                    period_label = formatdate(from_date, format_string="MMM") + "-" + formatdate(to_date, format_string="MMM")
                else:
                    period_label = formatdate(from_date, format_string="MMM")
                period_label += " " + str(year[0])
            
            columns.extend([
                {
                    "label": _("Volume") + " " + period_label,
                    "fieldtype": "Float",
                    "fieldname": f"volume_{period_label}".lower().replace("-", "_"),
                    "width": 120
                },
                {
                    "label": _("Value") + " " + period_label,
                    "fieldtype": "Currency",
                    "fieldname": f"value_{period_label}".lower().replace("-", "_"),
                    "width": 120
                },
                {
                    "label": _("% Contr. Value") + " " + period_label,
                    "fieldtype": "Percent",
                    "fieldname": f"contribution_{period_label}".lower().replace("-", "_"),
                    "width": 120
                }
            ])

    if filters["period"] != "Yearly":
        columns.extend([
            {
                "label": _("Total Volume"),
                "fieldtype": "Float",
                "fieldname": "total_volume",
                "width": 120
            },
            {
                "label": _("Total Value"),
                "fieldtype": "Currency",
                "fieldname": "total_value",
                "width": 120
            },
            {
                "label": _("Total % Contr."),
                "fieldtype": "Percent",
                "fieldname": "total_contribution",
                "width": 120
            }
        ])

    return columns

def get_fiscal_year_dates(filters):
    start_date = frappe.db.get_value("Fiscal Year", filters.from_fiscal_year, "year_start_date")
    end_date = frappe.db.get_value("Fiscal Year", filters.to_fiscal_year, "year_end_date")
    return start_date, end_date

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

    volumes = []
    values = []
    
    for row in data:
        row_values = row[1:]
        for i in range(0, len(row_values), 3):
            if i//3 < len(labels):
                volumes.append(row_values[i])
                values.append(row_values[i+1])

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": _("Volume"), "values": volumes, "chartType": "bar"},
                {"name": _("Value"), "values": values, "chartType": "line"}
            ]
        },
        "type": "bar"
    }