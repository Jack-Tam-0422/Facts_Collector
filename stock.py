import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
from helpers import apology, login_required, lookup, usd

def check_interval(interval):
        if interval == "week":
            return "wk"
        elif interval == "month":
            return "mo"
        else:
            return "y"


def check_period(period):
    period_for = "1"

    if period:
        period_for = period
    return period_for


def get_data_for_chart(symbol, period_for_display):
    ticket = yf.Ticker(symbol)
    df_hist = ticket.history(period=period_for_display)
    df_hist.reset_index(inplace=True)

    # Convert the DataFrame to a JSON object with the date formatted as "YYYY-MM-DD"
    df_hist["Date"] = df_hist["Date"].dt.strftime("%Y-%m-%d")
    data = df_hist.to_json(orient='records')
    return data


def get_stock_profitability(sym):
    symbol = yf.Ticker(sym)
    stock_info = {}

    # Perform necessary operations to retrieve the data
    # Replace {symbol} with the actual API call or data retrieval logic
    # investor valuation
    dividend_yield = symbol.info.get('dividendYield', 0)
    formatted_dividend_yield = '{:.2%}'.format(dividend_yield)
    stock_info['Dividend Yield'] = formatted_dividend_yield
    net_income = symbol.info.get('netIncomeToCommon', 0)
    net_income_in_millions = round(net_income / 1000000, 2)
    formatted_net_income = '${:,.0f}M'.format(net_income_in_millions)
    stock_info['Net Income to Commmon Stockholders'] = formatted_net_income
    stock_info['Operating Margins'] = round(symbol.info.get('operatingMargins', 0), 2)
    stock_info['Profit Margins'] = round(symbol.info.get('profitMargins', 0), 2)
    return stock_info


def get_stock_operation(sym):
    symbol = yf.Ticker(sym)
    stock_info = {}

    total_revenue = symbol.info.get('totalRevenue', 0)
    total_revenue_in_millions = round(total_revenue / 1000000, 2)
    formatted_total_revenue = '${:,.0f}M'.format(total_revenue_in_millions)
    stock_info['Total Revenue'] = formatted_total_revenue
    stock_info['Revenue Growth'] = round(symbol.info.get('revenueGrowth', 0), 2)
    stock_info['Return on Assets'] = round(symbol.info.get('returnOnAssets', 0), 2)
    stock_info['Return on Equity'] = round(symbol.info.get('returnOnEquity', 0), 2)

    return stock_info
#basic info
def get_stock_basic_info(sym):
    symbol = yf.Ticker(sym)
    stock_info = {}

    market_cap = symbol.info.get('marketCap', 0)
    market_cap_in_millions = round(market_cap / 1000000, 2)
    formatted_market_cap = '${:,.0f}M'.format(market_cap_in_millions)
    stock_info['Market Cap'] = formatted_market_cap
    stock_info['Website'] = symbol.info.get('website', "/")
    stock_info['Industry'] = symbol.info.get('industry', "/")
    full_time_employees = symbol.info.get('fullTimeEmployees')
    if full_time_employees is None:
        stock_info['Full Time Employees'] = "/"
    else:
        stock_info['Full Time Employees'] = '{:,.2f}'.format(full_time_employees)

    return stock_info

# valuation
def get_stock_valuation(sym):
    symbol = yf.Ticker(sym)
    stock_info = {}

    stock_info['Trailing Pe'] = round(symbol.info.get('trailingPE', 0), 2)
    stock_info['Forward Pe'] = round(symbol.info.get('forwardPE', 0), 2)
    stock_info['Book Value'] = round(symbol.info.get('bookValue', 0), 2)
    stock_info['Price to Book'] = round(symbol.info.get('priceToBook', 0), 2)

    return stock_info



def return_portfolio_table(portfolio_db):
    df = pd.DataFrame(portfolio_db)

    user_stock = [item['symbol'] for item in portfolio_db]

    current_stock_price = {}

    for stock in user_stock:
        current_stock_price[stock] = lookup(stock)["price"]

    current_stock_price_df = pd.DataFrame.from_dict(current_stock_price, orient='index', columns=['price'])

    # Reset the index of the DataFrame to create a 'symbol' column
    current_stock_price_df.reset_index(inplace=True)
    current_stock_price_df.rename(columns={'index': 'symbol'}, inplace=True)

    merge_df = pd.DataFrame()
    try:
        merge_df = pd.merge(df, current_stock_price_df, on = "symbol", how = "inner")
        merge_df['Current position value($USD)'] = merge_df['price'] * merge_df['quantity_hold']
        merge_df['Net gains($USD)'] = merge_df['Current position value($USD)'] - merge_df['net_costs']
        merge_df['net_costs_per_share'].round(2)
        merge_df['% gain'] = (merge_df['Net gains($USD)'] / merge_df['net_costs'] * 100).round(2)
        merge_df = merge_df.rename(columns={'symbol':'Symbol','quantity_hold':'Quantity Holding', 'net_costs_per_share':'Net Costs per Share($USD)','net_costs':'Net Costs($USD)','price':'Current Price($USD)'})

        format_func = lambda x: '{:,.2f}'.format(x)
        columns_to_format = ['Net Costs per Share($USD)', 'Quantity Holding', 'Net Costs($USD)', 'Current Price($USD)', 'Current position value($USD)', 'Net gains($USD)']
        merge_df[columns_to_format] = merge_df[columns_to_format].applymap(format_func)
    except:
        pass


    if merge_df.empty:
        portfolio_table = ''  # or portfolio_table = None
    else:
        portfolio_table = merge_df.to_html(index=False)
    return portfolio_table, merge_df


def google_search(query):
    url = f"https://www.google.com/search?q={query}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Safari/537.36"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.text

def retrieve_top_results(html_content, num_results):
    soup = BeautifulSoup(html_content, 'html.parser')
    search_results = soup.select('.g')

    results = []
    for result in search_results[:num_results]:
        title = result.select_one('.LC20lb').text
        url = result.select_one('.yuRUbf a')['href']
        snippet = result.select_one('.VwiC3b').text

        # Get the preview of the first 200 words
        preview = ' '.join(snippet.split()[:200])

        results.append({'title': title, 'url': url, 'preview': preview})

    return results


def get_sumamry_table(merge_df, user_cash_db):
        try:
            df_summary = pd.DataFrame(user_cash_db)
            df_summary['Total Equity Value($USD)'] = merge_df['Current position value($USD)'].str.replace(',', '').astype(float).sum()
            df_summary['Total Portfolio Value($USD)'] = df_summary['Total Equity Value($USD)'] + df_summary['cash']
            df_summary['Net Total Gain($USD)'] = df_summary['Total Portfolio Value($USD)'] - 10000
            df_summary['Total % Gain'] = (df_summary['Net Total Gain($USD)']  / 10000).round(2).map('{:.2%}'.format)
            df_summary = df_summary.rename(columns={'cash':'Cash($USD)'})

            format_func = lambda x: '{:,.0f}'.format(x)
            columns_to_format = ['Cash($USD)', 'Total Equity Value($USD)', 'Total Portfolio Value($USD)', 'Net Total Gain($USD)']
            df_summary[columns_to_format] = df_summary[columns_to_format].applymap(format_func)
            return df_summary
        except:
            return pd.DataFrame()
