# Copyright (c) 2025, kunleadenuga and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

from erpnext.accounts.report.financial_statements import (
    compute_growth_view_data,
    compute_margin_view_data,
    get_columns,
    get_data,
    get_filtered_list_for_consolidated_report,
    get_period_list,
)


def execute(filters=None):
    period_list = get_period_list(
        filters.from_fiscal_year,
        filters.to_fiscal_year,
        filters.period_start_date,
        filters.period_end_date,
        filters.filter_based_on,
        filters.periodicity,
        company=filters.company,
    )

    income = get_data(
        filters.company,
        "Income",
        "Credit",
        period_list,
        filters=filters,
        accumulated_values=filters.accumulated_values,
        ignore_closing_entries=True,
        ignore_accumulated_values_for_fy=True,
    )

    expense = get_data(
        filters.company,
        "Expense",
        "Debit",
        period_list,
        filters=filters,
        accumulated_values=filters.accumulated_values,
        ignore_closing_entries=True,
        ignore_accumulated_values_for_fy=True,
    )

    net_profit_loss = get_net_profit_loss(
        income, expense, period_list, filters.company, filters.presentation_currency
    )

    data = []
    data.extend(income or [])
    data.extend(expense or [])

    empty_row = None
    for exp in expense:
        if exp.get('indent') == 0.0:
            empty_row = {key: None for key in exp.keys()}
            break


    filtered_data = calculate_financial_metrics(income, expense, filters)



    if net_profit_loss:
        data.append(net_profit_loss)

    columns = get_columns(filters.periodicity, period_list, filters.accumulated_values, filters.company)

    currency = filters.presentation_currency or frappe.get_cached_value(
        "Company", filters.company, "default_currency"
    )
    chart = get_chart_data(filters, columns, income, expense, net_profit_loss, currency)

    report_summary, primitive_summary = get_report_summary(
        period_list, filters.periodicity, income, expense, net_profit_loss, currency, filters
    )

    if filters.get("selected_view") == "Growth":
        compute_growth_view_data(data, period_list)

    if filters.get("selected_view") == "Margin":
        compute_margin_view_data(data, period_list, filters.accumulated_values)


    
    
    # Load Our Custom Modified data
    # if not (filters.get("selected_view") == "Growth" or filters.get("selected_view") == "Margin"):
    for col in columns:
            if col.get('fieldname') == 'account':
                col['fieldtype'] = 'Data'
                col['label'] = 'Profit and Loss Account'

    data = []
    data.extend(filtered_data or [])
    if net_profit_loss:
        data.append(net_profit_loss)
            
    data.append(empty_row)

        
    return columns, data, None, chart, report_summary, primitive_summary


def calculate_financial_metrics(income, expense, filters):
    filtered_data = []
    
    # Process income entries
    for inc in income:
        if inc.get('indent') == 0.0:
            inc['account_name'] = inc.get('account').split(" - ")[1]
            inc['account'] = inc.get('account_name')
            filtered_data.append(inc)
    
    # Initialize rows
    empty_row = None
    depreciation_row = {'account_name': 'Depreciation & Amortisation Expenses', 
                       'account': 'Depreciation & Amortisation Expenses'}
    finance_cost_row = {'account_name': 'Finance Cost', 
                       'account': 'Finance Cost'}
    gross_profit = None

    # Process expense entries
    for exp in expense:
        if exp.get('indent') == 0.0:
            empty_row = {key: None for key in exp.keys()}

            exp['account_name'] = exp.get('account').split(" - ")[1]
            exp['account'] = exp.get('account_name')
            filtered_data.append(exp)
            
            # Calculate Gross Profit when cost entry is found
            if 'cost of' in exp.get('account_name').lower():
                # Initialize gross profit with all keys
                gross_profit = {key: None for key in exp.keys()}
                
                # Set the text fields
                gross_profit['account'] = 'Gross Profit'
                gross_profit['account_name'] = 'Gross Profit'
                
                # Calculate numeric fields
                for key in gross_profit:
                    if key not in ['account', 'account_name', 'indent']:
                        try:
                            value1 = filtered_data[0].get(key, 0)
                            value2 = filtered_data[1].get(key, 0)
                            
                            if isinstance(value1, (int, float, str)) and isinstance(value2, (int, float, str)):
                                try:
                                    gross_profit[key] = float(value1 or 0) - float(value2 or 0)
                                except (ValueError, TypeError):
                                    gross_profit[key] = None
                        except (ValueError, TypeError):
                            gross_profit[key] = None
                            
                filtered_data.append(empty_row)
                filtered_data.append(gross_profit)
                

        if exp.get('indent') == 1.0:
            if 'operating expense' in exp.get('parent_account').lower():
                # exp['indent'] = 0.0
                filtered_data.append(exp)

    
    # Initialize rows with all fields from exp
    depreciation_row = {key: None for key in exp.keys()}
    finance_cost_row = {key: None for key in exp.keys()}
    # empty_row = {key: None for key in exp.keys()}
    
    # Set basic info for rows
    depreciation_row['account'] = 'Depreciation & amortisation'
    depreciation_row['account_name'] = 'Depreciation & amortisation'
    finance_cost_row['account'] = 'Finance charges'
    finance_cost_row['account_name'] = 'Finance charges'
    
    # Process depreciation and finance charges
    for exp in expense:
        if exp.get('indent') == 1.0:
            # Handle depreciation
            if 'depreciation & amortisation'.lower() in exp.get('account').lower():
                frappe.log_error("depreciation row", exp)
                for key in exp.keys():
                    if key not in ['account', 'account_name', 'indent']:
                        try:
                            depreciation_row[key] = float(exp.get(key) or 0)
                        except (ValueError, TypeError):
                            depreciation_row[key] = None
            
            # Handle finance charges
            if 'finance charges'.lower() in exp.get('account').lower():
                for key in exp.keys():
                    if key not in ['account', 'account_name', 'indent']:
                        try:
                            finance_cost_row[key] = float(exp.get(key) or 0)
                        except (ValueError, TypeError):
                            finance_cost_row[key] = None
    
    filtered_data.append(empty_row)
    
    # Calculate EBITDA
    
    row_main_keys = None
    for exp1 in expense:
        if exp1.get('indent') == 1.0:
            row_main_keys = exp1
            break

    ebitda = {key: None for key in row_main_keys.keys()}
    ebitda['account'] = 'EBITDA'
    ebitda['account_name'] = 'EBITDA'
    
    for key in row_main_keys.keys():
        if key not in ['account', 'account_name', 'indent']:
            try:
                value1 = filtered_data[3].get(key, 0)
                value2 = filtered_data[4].get(key, 0)
                ebitda[key] = float(value1 or 0) - float(value2 or 0)
            except (ValueError, TypeError):
                ebitda[key] = None
    
    filtered_data.append(ebitda)
    filtered_data.append(empty_row)
    
    # Add depreciation row
    filtered_data.append(depreciation_row)
    
    # Calculate EBIT
    ebit = {key: None for key in row_main_keys.keys()}
    ebit['account'] = 'EBIT'
    ebit['account_name'] = 'EBIT'
    
    for key in row_main_keys.keys():
        if key not in ['account', 'account_name', 'indent']:
            try:
                ebitda_value = float(ebitda.get(key) or 0)
                depreciation_value = float(depreciation_row.get(key) or 0)
                ebit[key] = ebitda_value - depreciation_value
            except (ValueError, TypeError):
                ebit[key] = None
    
    filtered_data.append(ebit)
    filtered_data.append(empty_row)
    
    # Add finance cost row
    filtered_data.append(finance_cost_row)
    
    # Calculate Profit Before Tax
    profit_before_tax_row = {key: None for key in row_main_keys.keys()}
    profit_before_tax_row['account'] = 'Profit Before Tax'
    profit_before_tax_row['account_name'] = 'Profit Before Tax'
    
    for key in row_main_keys.keys():
        if key not in ['account', 'account_name', 'indent']:
            try:
                ebit_value = float(ebit.get(key) or 0)
                finance_value = float(finance_cost_row.get(key) or 0)
                profit_before_tax_row[key] = ebit_value - finance_value
            except (ValueError, TypeError):
                profit_before_tax_row[key] = None
    
    filtered_data.append(profit_before_tax_row)
    filtered_data.append(empty_row)
    
    return filtered_data


def get_report_summary(
    period_list, periodicity, income, expense, net_profit_loss, currency, filters, consolidated=False
):
    net_income, net_expense, net_profit = 0.0, 0.0, 0.0

    # from consolidated financial statement
    if filters.get("accumulated_in_group_company"):
        period_list = get_filtered_list_for_consolidated_report(filters, period_list)

    if filters.accumulated_values:
        # when 'accumulated_values' is enabled, periods have running balance.
        # so, last period will have the net amount.
        key = period_list[-1].key
        if income:
            net_income = income[-2].get(key)
        if expense:
            net_expense = expense[-2].get(key)
        if net_profit_loss:
            net_profit = net_profit_loss.get(key)
    else:
        for period in period_list:
            key = period if consolidated else period.key
            if income:
                net_income += income[-2].get(key)
            if expense:
                net_expense += expense[-2].get(key)
            if net_profit_loss:
                net_profit += net_profit_loss.get(key)

    if len(period_list) == 1 and periodicity == "Yearly":
        profit_label = _("Profit This Year")
        income_label = _("Total Income This Year")
        expense_label = _("Total Expense This Year")
    else:
        profit_label = _("Net Profit")
        income_label = _("Total Income")
        expense_label = _("Total Expense")

    return [
        {"value": net_income, "label": income_label, "datatype": "Currency", "currency": currency},
        {"type": "separator", "value": "-"},
        {"value": net_expense, "label": expense_label, "datatype": "Currency", "currency": currency},
        {"type": "separator", "value": "=", "color": "blue"},
        {
            "value": net_profit,
            "indicator": "Green" if net_profit > 0 else "Red",
            "label": profit_label,
            "datatype": "Currency",
            "currency": currency,
        },
    ], net_profit


def get_net_profit_loss(income, expense, period_list, company, currency=None, consolidated=False):
    total = 0
    net_profit_loss = {
        "account_name": _("Profit for the year"),
        "account":  _("Profit for the year"),
        "warn_if_negative": True,
        "currency": currency or frappe.get_cached_value("Company", company, "default_currency"),
    }

    has_value = False

    for period in period_list:
        key = period if consolidated else period.key
        total_income = flt(income[-2][key], 3) if income else 0
        total_expense = flt(expense[-2][key], 3) if expense else 0

        net_profit_loss[key] = total_income - total_expense

        if net_profit_loss[key]:
            has_value = True

        total += flt(net_profit_loss[key])
        net_profit_loss["total"] = total

    if has_value:
        return net_profit_loss


def get_chart_data(filters, columns, income, expense, net_profit_loss, currency):
    labels = [d.get("label") for d in columns[2:]]

    income_data, expense_data, net_profit = [], [], []

    for p in columns[2:]:
        if income:
            income_data.append(income[-2].get(p.get("fieldname")))
        if expense:
            expense_data.append(expense[-2].get(p.get("fieldname")))
        if net_profit_loss:
            net_profit.append(net_profit_loss.get(p.get("fieldname")))

    datasets = []
    if income_data:
        datasets.append({"name": _("Income"), "values": income_data})
    if expense_data:
        datasets.append({"name": _("Expense"), "values": expense_data})
    if net_profit:
        datasets.append({"name": _("Net Profit/Loss"), "values": net_profit})

    chart = {"data": {"labels": labels, "datasets": datasets}}

    if not filters.accumulated_values:
        chart["type"] = "bar"
    else:
        chart["type"] = "line"

    chart["fieldtype"] = "Currency"
    chart["options"] = "currency"
    chart["currency"] = currency

    return chart


