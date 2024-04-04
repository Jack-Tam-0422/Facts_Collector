import os
import yfinance as yf
import pandas as pd

from stock import check_interval, check_period, get_data_for_chart, get_sumamry_table, get_stock_basic_info, get_stock_profitability, get_stock_operation, get_stock_valuation, return_portfolio_table, google_search, retrieve_top_results
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required, lookup, usd


# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    return render_template("index.html")



@app.route("/stimulator", methods=["GET"])
@login_required
def stimulator():
    """Buy shares of stock"""
    if request.method == "GET":

        user_id = session["user_id"]
        portfolio_db = db.execute(
        "SELECT symbol, "
        "sum(case when transaction_type = 'b' then quantity else quantity * (-1) end) as quantity_hold, "
        "sum(case when transaction_type = 'b' then transacted_price_per_share * quantity else (transacted_price_per_share * quantity) * (-1) end) / "
        "sum(case when transaction_type = 'b' then quantity else quantity * (-1) end) as net_costs_per_share, "
        "sum(case when transaction_type = 'b' then transacted_price_per_share * quantity else (transacted_price_per_share * quantity) * (-1) end) as net_costs "
        "FROM transactions "
        "WHERE user_id = :id "
        "group by symbol",
        id=user_id
        )
        portfolio_table, merge_df = return_portfolio_table(portfolio_db)

        user_cash_db = db.execute("SELECT cash FROM users WHERE id = :id", id=user_id)
        df_summary = get_sumamry_table(merge_df, user_cash_db)



        return render_template("stimulator.html", portfolio_table=portfolio_table, summary_table = df_summary.to_html(index=False))




@app.route("/buy", methods=["POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")

        if not symbol:
            return apology("Must Give Symbol")

        stock = lookup(symbol.upper())

        if stock == None:
            return apology("Symbol does not exist")

        if not shares or not shares.isdigit() or int(shares) <= 0:
            return apology("Invalid number of shares provided.")
        else:
            shares = int(request.form.get("shares"))

        transaction_value = shares * stock["price"]
        price_bought = usd(transaction_value)

        user_id = session["user_id"]
        user_cash_db = db.execute("SELECT cash FROM users WHERE id = :id", id=user_id)

        user_cash = user_cash_db[0]["cash"]

        if user_cash < transaction_value:
            return apology("Not Enough Money")

        uptd_cash = user_cash - transaction_value

        db.execute("UPDATE users SET cash = ? WHERE id = ?", uptd_cash, user_id)

        db.execute(
            "INSERT INTO transactions (user_id, symbol, quantity, transacted_price_per_share, transaction_type) VALUES (?, ?, ?, ?, ?)",
            user_id,
            stock["symbol"],
            shares,
            stock["price"],
            "b"
        )

        flash(f"Bought {shares} shares of {symbol} for {price_bought}!")

        return redirect('/stimulator')


@app.route("/sell", methods=["POST"])
@login_required
def sell():
    """Sell shares of stock"""

    if request.method == "POST":
        symbol_raw = request.form.get("symbol")
        symbol = symbol_raw.upper()
        shares = request.form.get("shares")

        if not symbol:
            return apology("Must Give Symbol")

        stock = lookup(symbol.upper())

        if stock == None:
            return apology("Symbol does not exist")

        if not shares or not shares.isdigit() or int(shares) <= 0:
            return apology("Share Not allow")
        else:
            shares = int(request.form.get("shares"))

        transaction_value = shares * stock["price"]
        price_sold = usd(transaction_value)

        user_id = session["user_id"]
        user_cash_db = db.execute("SELECT cash FROM users WHERE id = :id", id=user_id)
        user_cash = user_cash_db[0]["cash"]

        user_shares = db.execute(
            "SELECT sum(case when transaction_type = 'b' then quantity else quantity * (-1) end) as quantity FROM transactions WHERE user_id=:id AND symbol = :symbol GROUP BY symbol",
            id=user_id,
            symbol=symbol,
        )

        try:
            user_shares_real = user_shares[0]["quantity"]
        except:
            return apology("You don't have any shares to sell.")

        if not user_shares:
            return apology("You don't have any shares to sell.")


        if shares >= user_shares_real:
            return apology("You don't have enough shares to sell.")

        uptd_cash = user_cash + transaction_value

        db.execute("UPDATE users SET cash = ? WHERE id = ?", uptd_cash, user_id)

        db.execute(
            "INSERT INTO transactions (user_id, symbol, quantity, transacted_price_per_share, transaction_type) VALUES (?, ?, ?, ?, ?)",
            user_id,
            stock["symbol"],
            shares,
            stock["price"],
            "s"
        )

        flash(f"Sold {shares} shares of {symbol} for {price_sold}!")

        return redirect('/stimulator')


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")
    else:
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username:
            return apology("Must Give Username")
        if not password:
            return apology("Must Give Password")
        if not confirmation:
            return apology("Must Give Confirmation")
        if password != confirmation:
            return apology("Password do not match")

        hash = generate_password_hash(password)

        try:
            new_user = db.execute(
                "INSERT INTO users (username, hash) VALUES (?, ?)", username, hash
            )
        except:
            return apology("Username already exists")

        session["user_id"] = new_user

        return redirect("/")

@app.route("/stock_graph", methods=["GET", "POST"])
@login_required

def stock_graph():
    if request.method == "POST":
        symbol = str(request.form.get("symbol"))
        stock = lookup(symbol.upper())

        period_for = check_period(str(request.form.get("period")))
        interval = check_interval(str(request.form.get("interval")))
        period_for_display = f"{period_for}{interval}"
        basic_info ={}
        operation ={}
        profitability ={}
        valuation ={}

        if stock == None:
            symbol = "AAPL"
            data = get_data_for_chart(symbol, period_for_display)
            basic_info = get_stock_basic_info(str(symbol))
            operation = get_stock_operation(str(symbol))
            profitability = get_stock_profitability(str(symbol))
            valuation = get_stock_valuation(str(symbol))

            flash(f"Stock Symbol not found. Here is the stock price of AAPL.")
            return render_template('stock_graph.html', data=data, symbol=symbol, basic_info=basic_info,operation=operation,profitability=profitability,valuation=valuation)

        else:

            data = get_data_for_chart(symbol, period_for_display)
            basic_info = get_stock_basic_info(str(symbol))
            operation = get_stock_operation(str(symbol))
            profitability = get_stock_profitability(str(symbol))
            valuation = get_stock_valuation(str(symbol))

            symbol = symbol.upper()

            return render_template('stock_graph.html', data=data, symbol=symbol, basic_info=basic_info,operation=operation,profitability=profitability,valuation=valuation)

    else:
        symbol = "AAPL"
        data = get_data_for_chart(symbol, "1y")
        basic_info = get_stock_basic_info(str(symbol))
        operation = get_stock_operation(str(symbol))
        profitability = get_stock_profitability(str(symbol))
        valuation = get_stock_valuation(str(symbol))
        return render_template('stock_graph.html', data=data, symbol=symbol, basic_info=basic_info,operation=operation,profitability=profitability,valuation=valuation)


@app.route("/google", methods=["GET", "POST"])
@login_required
def google():
    """Show portfolio of stocks"""

    if request.method == "GET":
        return render_template("google.html")

    else:
        try:
            symbol = str(request.form.get("symbol"))
            search_query = f"{symbol} stock news"
            search_query_news = f"{symbol} news"
            search_results = google_search(search_query)
            search_results_news = google_search(search_query_news)

            # Retrieve the top 5 search results
            top_results = retrieve_top_results(search_results, 5)
            top_results_news = retrieve_top_results(search_results_news, 5)

            return render_template("google.html",results=top_results, results_news=top_results_news)
        except:
            flash(f"Please try search something else")
            return render_template("google.html")
