# Copyright (c) 2025, kunleadenuga and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import flt

from erpnext.accounts.report.financial_statements import (
    compute_growth_view_data,
    compute_margin_view_data,
    get_data,
    get_filtered_list_for_consolidated_report,
    get_period_list,
)

from erpnext.accounts.report.budget_variance_report.budget_variance_report import (
    execute as budget_variance_report
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
    
    frappe.log_error("Income", income)
    frappe.log_error("Expense", expense)

    empty_row = None
    for exp in expense:
        if exp.get('indent') == 0.0:
            empty_row = {key: None for key in exp.keys()}
            break
    
    # months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']

    # for month in months:
    #     empty_row[f'budget_{month}']

    filtered_data = calculate_financial_metrics(income, expense, filters)



    if net_profit_loss:
        data.append(net_profit_loss)

    columns = get_columns(filters.periodicity, period_list, filters.accumulated_values, filters.company)

    currency = filters.presentation_currency or frappe.get_cached_value(
        "Company", filters.company, "default_currency"
    )
    # chart = get_chart_data(filters, columns, income, expense, net_profit_loss, currency)

    # report_summary, primitive_summary = get_report_summary(
    #     period_list, filters.periodicity, income, expense, net_profit_loss, currency, filters
    # )

    if filters.get("selected_view") == "Growth":
        compute_growth_view_data(data, period_list)

    if filters.get("selected_view") == "Margin":
        compute_margin_view_data(data, period_list, filters.accumulated_values)


    # if filters.get("from_fiscal_year"):
    

    # Load Our Custom Modified data
    # if not (filters.get("selected_view") == "Growth" or filters.get("selected_view") == "Margin"):

    frappe.log_error("columns", columns)
    for col in columns:
            if col.get('fieldname') == 'account':
                col['fieldtype'] = 'Data'
                col['label'] = ''

    data = []
    data.extend(filtered_data or [])
    if net_profit_loss:
        data.append(net_profit_loss)

    # for key in data[0]:
    #     empty_row[key] = None

    filters['period'] = filters.get('periodicity')
    filters['budget_against'] = "Cost Center"
    _, budget_data, _, _ = budget_variance_report(filters)
    frappe.log_error("budget_data", budget_data)

    budget_grouping = [
        {
            'account': '7001 - Revenue from ordinary line of Business - SSWCH',
            'budget': 0,
            'row': 'Revenue'
        },
        {
            'account': '7400 - Revenue from Non line of business - SSWCH',
            'budget': 0,
            'row': 'Other Expenses'
        }
    ]

    year_list = [str(year) for year in range(int(filters['from_fiscal_year']), int(filters['to_fiscal_year']) + 1)]

    # Fetch budgets using the year list
    budgets = frappe.db.get_all(
        "Budget",
        filters={
            'company': filters.company,
            'budget_against': 'Cost Center',
            'fiscal_year': ['in', year_list],  # Use the generated year list
            'docstatus': 1  # Ensure only submitted budgets are fetched
        },
    )


    budget_grouping_on_parent = {}
    for b in budgets:
        current_budget = frappe.get_doc("Budget", b)
        budget_grouping_on_parent[current_budget.fiscal_year] = {}
        
        for budget_row in current_budget.accounts:
            account = frappe.get_doc("Account", budget_row.account)
        #    account.parent_account
            current_parent = account.parent_account
            parent_acc_doc = {}
            parent_acc_doc['parent_account'] = True #in start
            prev_acc = None
            # budget_amount = 0

            
            while(True):
                parent_acc_doc = frappe.get_doc("Account", current_parent)
                # if hasattr(parent_acc_doc, 'parent_account') and parent_acc_doc.parent_account:
                if not parent_acc_doc.parent_account and parent_acc_doc.is_group:
                    if 'cost of sales' in parent_acc_doc.name.lower():
                        prev_acc = parent_acc_doc
                        # so we will get the sum in the Cost Of Sales not in its child like direct and stock expenses
                    break

                prev_acc = parent_acc_doc
                current_parent = parent_acc_doc.parent_account
                
            if prev_acc:
                # Check if the account name exists in the dictionary
                key_name = prev_acc.name.split("-")[1].strip()
                if key_name not in budget_grouping_on_parent[current_budget.fiscal_year]:
                    # 7001 - Revenue from ordinary line of Business - SSWCH to Revenue from ordinary line of Business
                    budget_grouping_on_parent[current_budget.fiscal_year][key_name] = 0

                # Add the budget amount
                budget_grouping_on_parent[current_budget.fiscal_year][key_name] += budget_row.budget_amount

            if parent_acc_doc:
                key_name = parent_acc_doc.name.split("-")[1].strip()
                if key_name not in budget_grouping_on_parent[current_budget.fiscal_year]:
                    # 7001 - Revenue from ordinary line of Business - SSWCH to Revenue from ordinary line of Business
                    budget_grouping_on_parent[current_budget.fiscal_year][key_name] = 0
                budget_grouping_on_parent[current_budget.fiscal_year][key_name] += budget_row.budget_amount

    # frappe.log_error("empty row", empty_row)
    frappe.log_error("budget grouping on parent", budget_grouping_on_parent)
            
    data.append(empty_row)

    # Revenue (line)
    months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']

    map_month = {
        'January': 'jan',
        'February': 'feb',
        'March': 'mar',
        'April': 'apr',
        'May': 'may',
        'June': 'jun',
        'July': 'jul',
        'August': 'aug',
        'September': 'sep',
        'October': 'oct',
        'November': 'nov',
        'December': 'dec'
    }


    for b in budgets:
        current_budget = frappe.get_doc("Budget", b)
        if current_budget.monthly_distribution:
            monthly_distribution = frappe.get_doc("Monthly Distribution", current_budget.monthly_distribution)

        for budget_year in budget_grouping_on_parent:

            for monthly_row in monthly_distribution.percentages:
                month = map_month[monthly_row.month] 

                actual_key_name = f'{month}_{budget_year}'
                budget_key_name = f'{month}_{budget_year}_budget'  
                achive_key_name = f'{month}_{budget_year}_achivement'  
                variance_key_name = f'{month}_{budget_year}_variance'  
                

                data[0][budget_key_name] = f"{((budget_grouping_on_parent[budget_year]['Revenue from ordinary line of Business'] * monthly_row.percentage_allocation)/100):.3f}"

                data[1][budget_key_name] = f"{((budget_grouping_on_parent[budget_year]['Cost of Sales'] * monthly_row.percentage_allocation)/100):.3f}"

                data[2][budget_key_name] = None
                
                # Update budget values for data[3] and data[5]
                data[3][budget_key_name] = float(data[0][budget_key_name]) - float(data[1][budget_key_name])

                data[5][budget_key_name] = f"{((budget_grouping_on_parent[budget_year]['Revenue from Non line of business'] * monthly_row.percentage_allocation) / 100):.3f}"

                data[7][budget_key_name] = f"{((budget_grouping_on_parent[budget_year]['Operating Expenses'] * monthly_row.percentage_allocation) / 100):.3f}"

                data[8][budget_key_name] = f"{((budget_grouping_on_parent[budget_year]['Administrative Expenses'] * monthly_row.percentage_allocation) / 100):.3f}"

                data[9][budget_key_name] = f"{((budget_grouping_on_parent[budget_year]['Repairs & maintenance Expenses'] * monthly_row.percentage_allocation) / 100):.3f}"

                data[10][budget_key_name] = f"{((budget_grouping_on_parent[budget_year]['Impairment charges'] * monthly_row.percentage_allocation) / 100):.3f}"

                data[11][budget_key_name] = f"{((budget_grouping_on_parent[budget_year]['Selling, distribution & marketing expenses'] * monthly_row.percentage_allocation) / 100):.3f}"

                data[12][budget_key_name] = f"{((budget_grouping_on_parent[budget_year]['Employees Benefit Expenses'] * monthly_row.percentage_allocation) / 100):.3f}"

                # data[14][budget_key_name] = f"{(data[3][budget_key_name] - data[7][budget_key_name] + data[5][budget_key_name]):.3f}"
                data[14][budget_key_name] = f"{(float(data[3][budget_key_name]) - float(data[7][budget_key_name]) + float(data[5][budget_key_name])):.3f}"

                data[16][budget_key_name] = f"{((budget_grouping_on_parent[budget_year]['Depreciation & amortisation expenses'] * monthly_row.percentage_allocation) / 100):.3f}"

                # data[17][budget_key_name] = f"{(data[14][budget_key_name] - data[16][budget_key_name]):.3f}"
                data[17][budget_key_name] = f"{(float(data[14][budget_key_name]) - float(data[16][budget_key_name])):.3f}"

                data[19][budget_key_name] = f"{((budget_grouping_on_parent[budget_year]['Finance charges'] * monthly_row.percentage_allocation) / 100):.3f}"

                # data[20][budget_key_name] = f"{(data[17][budget_key_name] - data[19][budget_key_name]):.3f}"
                data[20][budget_key_name] = f"{(float(data[17][budget_key_name]) - float(data[19][budget_key_name])):.3f}"



        # Achivement and Variance columns
    start_year = int(filters.get('from_fiscal_year'))
    end_year = int(filters.get('to_fiscal_year'))

    while(start_year<=end_year):
        for i, row in enumerate(data):

            if not row['account']:
                    continue

            for month in months:

                actual_key_name = f'{month}_{start_year}'
                budget_key_name = f'{month}_{start_year}_budget'  
                achive_key_name = f'{month}_{start_year}_achivement'  
                variance_key_name = f'{month}_{start_year}_variance'  

                act = float(data[i][actual_key_name]) or 0
                bud = float(data[i].get(budget_key_name, 0)) 

                if act:
                    data[i][achive_key_name] = f"{(((act - bud) / act) * 100.0):.3f}"
                else:
                    data[i][achive_key_name] = 0

                data[i][variance_key_name] = act - bud

                
        start_year += 1


    return columns, data, None, None, None, None


def get_columns(periodicity, period_list, accumulated_values=0, company=None, cash_flow=False):
    columns = [
        {
            "fieldname": "account",
            "label": _("Account") if not cash_flow else _("Section"),
            "fieldtype": "Link",
            "options": "Account",
            "width": 300,
        }
    ]
    if company:
        columns.append(
            {
                "fieldname": "currency",
                "label": _("Currency"),
                "fieldtype": "Link",
                "options": "Currency",
                "hidden": 1,
            }
        )
    for period in period_list:
        # "fieldname": f"budget_({month})_{year}",
        # "fieldname": f"variance_({month})_{year}",
        columns += [
            {
                "fieldname": f"{period.key}",
                "label": f"Actual ({period.label})",
                "fieldtype": "Currency",
                "options": "currency",
                "width": 150,
            },
            {
                "fieldname": f"{period.key}_budget",
                "label": f"Budget ({period.label})",
                "fieldtype": "Currency",
                "options": "currency",
                "width": 150,
            },
            {
                "fieldname": f"{period.key}_achivement",
                "label": f"% Ach ({period.label})",
                "fieldtype": "Percent",
                "width": 150,
            },
            {
                "fieldname": f"{period.key}_variance",
                "label": f"Variance ({period.label})",
                "fieldtype": "Currency",
                "options": "currency",
                "width": 150,
            },
            {
                "fieldname": "empty_column",
                "label": "",
                "fieldtype": "Data",
                "width": 80,
            },
        ]
    # if periodicity != "Yearly":
    #     if not accumulated_values:
    #         columns.append(
    #             {
    #                 "fieldname": "total",
    #                 "label": _("Total"),
    #                 "fieldtype": "Currency",
    #                 "width": 150,
    #                 "options": "currency",
    #             }
    #         )

    return columns



def calculate_financial_metrics(income, expense, filters):
    filtered_data = []
    
    # Process income entries
    frappe.log_error("income", income)
    # for inc in income:
    #     if inc.get('indent') == 0.0:
    #         inc['account_name'] = inc.get('account').split(" - ")[1]
    #         inc['account'] = inc.get('account_name')
    #         filtered_data.append(inc)
    
    revenue_row =  {'account_name': 'Revenue', 'account': 'Revenue'}
    # other_income_row =  {'account_name': 'Other Income', 'account': 'Other Income'}
    other_income_row =  None
    for inc in income:
        if inc.get('indent') == 1.0 and "Non line".lower() in inc.get('account').lower():
            inc['account_name'] = "Other Income"
            inc['account'] = "Other Income"
            inc['indent'] = 0.0
            other_income_row = inc
        if inc.get('indent') == 1.0 and not "Non line".lower() in inc.get('account').lower():
            inc['account_name'] = "Revenue"
            inc['account'] = "Revenue"
            inc['indent'] = 0.0
            filtered_data.append(inc)

    # Initialize rows
    empty_row = None
    depreciation_row = {'account_name': 'Depreciation & Amortisation Expenses', 
                       'account': 'Depreciation & Amortisation Expenses'}
    finance_cost_row = {'account_name': 'Finance Cost', 
                       'account': 'Finance Cost'}
    gross_profit = None
    operating_expenses = None

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
                filtered_data.append(empty_row)
                filtered_data.append(other_income_row)
                filtered_data.append(empty_row)
                
        if exp.get('indent') == 1.0:
            if 'operating expense' in exp.get('parent_account').lower() and "Depreciation & amortisation expenses".lower() not in exp.get("account").lower() and "Finance charges".lower()  not in exp.get("account").lower():
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
                # frappe.log_error("depreciation row", exp)
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
    # Update the operating expense subtract these two accounts value
    months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
    start_year = int(filters['from_fiscal_year'])
    end_year = int(filters['to_fiscal_year'])
    for month in months:
        if end_year >= start_year:
            key = f"{month}_{start_year}"
            filtered_data[7][key] -= (float(finance_cost_row[key]) + float(depreciation_row[key]))

        start_year += 1
    
    operating_expenses = filtered_data[7]

    
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
                value1 = gross_profit.get(key, 0)
                value2 = operating_expenses.get(key, 0)
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

    # Update Operating expense number subtract deperication and the finance expense
    # for key in filtered_data[7]:
    #     if key not in ['account', 'account_name', 'indent'] and finance_cost_row[key] and depreciation_row[key]:
    #         filtered_data[7][key] -= (float(finance_cost_row[key]) + float(depreciation_row[key]))
   
    

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


