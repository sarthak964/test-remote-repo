from fastmcp import FastMCP
import os
import sqlite3
import tempfile
import json

# Use temporary directory which should be writable
TEMP_DIR = tempfile.gettempdir()
DB_PATH = os.path.join(TEMP_DIR, "expenses.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

mcp = FastMCP("ExpenseTracker")


def init_db():
    try:
        with sqlite3.connect(DB_PATH) as c:
            c.execute("PRAGMA journal_mode=WAL")

            c.execute("""
                CREATE TABLE IF NOT EXISTS expenses(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    subcategory TEXT DEFAULT '',
                    note TEXT DEFAULT ''
                )
            """)

            c.execute(
                "INSERT OR IGNORE INTO expenses(date, amount, category) VALUES ('2000-01-01', 0, 'test')"
            )
            c.execute("DELETE FROM expenses WHERE category = 'test'")
            c.commit()

    except Exception as e:
        raise RuntimeError(f"Database initialization failed: {e}")


init_db()


@mcp.tool()
def add_expense(
    date: str,
    amount: float,
    category: str,
    subcategory: str = "",
    note: str = ""
):
    """Add a new expense entry to the database."""

    try:
        with sqlite3.connect(DB_PATH) as c:
            cur = c.execute(
                """
                INSERT INTO expenses
                (date, amount, category, subcategory, note)
                VALUES (?, ?, ?, ?, ?)
                """,
                (date, amount, category, subcategory, note)
            )

            expense_id = cur.lastrowid
            c.commit()

            return {
                "status": "success",
                "id": expense_id,
                "message": "Expense added successfully"
            }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@mcp.tool()
def list_expenses(start_date: str, end_date: str):
    """List expense entries within an inclusive date range."""

    try:
        with sqlite3.connect(DB_PATH) as c:
            cur = c.execute(
                """
                SELECT
                    id,
                    date,
                    amount,
                    category,
                    subcategory,
                    note
                FROM expenses
                WHERE date BETWEEN ? AND ?
                ORDER BY date DESC, id DESC
                """,
                (start_date, end_date)
            )

            cols = [d[0] for d in cur.description]

            return [
                dict(zip(cols, row))
                for row in cur.fetchall()
            ]

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@mcp.tool()
def summarize(
    start_date: str,
    end_date: str,
    category: str | None = None
):
    """Summarize expenses by category within an inclusive date range."""

    try:
        query = """
            SELECT
                category,
                SUM(amount) AS total_amount,
                COUNT(*) AS count
            FROM expenses
            WHERE date BETWEEN ? AND ?
        """

        params = [start_date, end_date]

        if category:
            query += " AND category = ?"
            params.append(category)

        query += """
            GROUP BY category
            ORDER BY total_amount DESC
        """

        with sqlite3.connect(DB_PATH) as c:
            cur = c.execute(query, params)

            cols = [d[0] for d in cur.description]

            return [
                dict(zip(cols, row))
                for row in cur.fetchall()
            ]

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@mcp.resource(
    "expense:///categories",
    mime_type="application/json"
)
def categories():
    """Return expense categories."""

    default_categories = {
        "categories": [
            "Food & Dining",
            "Transportation",
            "Shopping",
            "Entertainment",
            "Bills & Utilities",
            "Healthcare",
            "Travel",
            "Education",
            "Business",
            "Other"
        ]
    }

    try:
        with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
            return f.read()

    except FileNotFoundError:
        return json.dumps(default_categories, indent=2)

    except Exception as e:
        return json.dumps(
            {"error": str(e)},
            indent=2
        )


if __name__ == "__main__":
    # Claude Desktop
    # mcp.run()

    # For HTTP transport, use:
    mcp.run(transport="http", host="0.0.0.0", port=8000)