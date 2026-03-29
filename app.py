from flask import Flask, request, render_template_string, session
import pandas as pd

app = Flask(__name__)
app.secret_key = "cbre123"

df = pd.read_csv("C:/Users/Cade/positions.csv", encoding="latin1")

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>CBRE Open Positions</title>
    <style>
        body { font-family: Arial; padding: 20px; background: #f9f9f9; }
        h1 { color: #003087; }
        input { padding: 8px; font-size: 16px; margin: 5px; width: 300px; }
        button { padding: 8px 16px; font-size: 16px; background: #003087; color: white; border: none; cursor: pointer; margin: 5px; border-radius: 4px; }
        button:hover { background: #0051a8; }
        .menu { background: #f2f2f2; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .pagination { margin-top: 20px; }
        .pagination a { padding: 8px 12px; margin: 2px; background: #003087; color: white; text-decoration: none; border-radius: 4px; }
        .pagination a:hover { background: #0051a8; }
        .pagination span { padding: 8px 12px; margin: 2px; background: #ccc; border-radius: 4px; }
        .count { font-weight: bold; margin-top: 10px; color: #003087; }
        .grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-top: 20px; }
        .card { border: 1px solid #ddd; padding: 10px; border-radius: 4px; background: white; box-shadow: 1px 1px 4px rgba(0,0,0,0.1); position: relative; }
        .city { font-size: 14px; font-weight: bold; color: #333; margin-bottom: 4px; }
        .card a.name { font-size: 13px; color: #003087; text-decoration: none; }
        .card a.name:hover { text-decoration: underline; }
        .not-btn { position: absolute; top: 8px; right: 8px; background: #cc0000; color: white; border: none; border-radius: 4px; padding: 2px 6px; font-size: 11px; cursor: pointer; text-decoration: none; }
        .not-btn:hover { background: #990000; }
    </style>
</head>
<body>
    <h1>CBRE Open Positions</h1>

    <div class="menu">
        <b>Search by State(s)</b><br>
        <small>Enter one or more states separated by commas (e.g. TX, CA, NY)</small><br><br>
        <form method="GET" action="/search">
            <input type="text" name="states" placeholder="e.g. TX, CA, NY" value="{{ states or '' }}">
            <button type="submit">Search</button>
        </form>
        {% if excluded %}
            <br><b>Excluded names ({{ excluded|length }}):</b> {{ excluded|join(", ") }}
            <a href="/clear?states={{ states }}" style="margin-left:10px; color: #cc0000;">Clear All</a>
        {% endif %}
    </div>

    {% if results %}
        <div class="count">Found {{ total }} positions for: {{ states }} — Page {{ page }} of {{ total_pages }}</div>
        <div class="grid">
            {% for row in results %}
            <div class="card">
                <a href="/not?name={{ row.name|urlencode }}&states={{ states }}&page={{ page }}" class="not-btn">NOT</a>
                <div class="city">{{ row.city }}</div>
                <a href="/detail?name={{ row.name|urlencode }}" target="_blank" class="name">{{ row.name }}</a>
            </div>
            {% endfor %}
        </div>

        <div class="pagination">
            {% if page > 1 %}
                <a href="/search?states={{ states }}&page={{ page - 1 }}">← Prev</a>
            {% endif %}
            {% for p in range(1, total_pages + 1) %}
                {% if p == page %}
                    <span>{{ p }}</span>
                {% else %}
                    <a href="/search?states={{ states }}&page={{ p }}">{{ p }}</a>
                {% endif %}
            {% endfor %}
            {% if page < total_pages %}
                <a href="/search?states={{ states }}&page={{ page + 1 }}">Next →</a>
            {% endif %}
        </div>
    {% endif %}

</body>
</html>
"""

DETAIL_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ name }}</title>
    <style>
        body { font-family: Arial; padding: 40px; background: #f9f9f9; }
        h1 { color: #003087; }
        table { border-collapse: collapse; width: 100%; margin-top: 20px; }
        th { background: #003087; color: white; padding: 10px; text-align: left; }
        td { border: 1px solid #ddd; padding: 10px; }
        tr:nth-child(even) { background: #f2f2f2; }
    </style>
</head>
<body>
    <h1>{{ name }}</h1>
    <table>
        {% for key, val in details.items() %}
        <tr>
            <th>{{ key }}</th>
            <td>{{ val }}</td>
        </tr>
        {% endfor %}
    </table>
    <br>
    <a href="javascript:window.close()">Close</a>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/search", methods=["GET"])
def search():
    states = request.args.get("states", "")
    page = int(request.args.get("page", 1))
    per_page = 50

    excluded = session.get("excluded", [])

    state_list = [s.strip() for s in states.split(",")]
    mask = df.iloc[:, 4].str.contains("|".join(state_list), case=False, na=False)
    filtered = df[mask].reset_index(drop=True)

    filtered = filtered[~filtered.iloc[:, 1].isin(excluded)]
    filtered = filtered.sort_values(by=filtered.columns[1]).reset_index(drop=True)

    total = len(filtered)
    total_pages = max(1, -(-total // per_page))
    start = (page - 1) * per_page
    end = start + per_page
    page_df = filtered.iloc[start:end]

    results = []
    for _, row in page_df.iterrows():
        name = str(row.iloc[1])
        city = str(row.iloc[5])
        results.append({"name": name, "city": city})

    return render_template_string(HTML, results=results, states=states,
                                   page=page, total=total, total_pages=total_pages,
                                   excluded=excluded)

@app.route("/detail")
def detail():
    name = request.args.get("name", "")
    match = df[df.iloc[:, 1] == name]
    if match.empty:
        return "Not found", 404
    row = match.iloc[0]
    details = {col: row[col] for col in df.columns}
    return render_template_string(DETAIL_HTML, name=name, details=details)

@app.route("/not")
def not_name():
    name = request.args.get("name", "")
    states = request.args.get("states", "")

    excluded = session.get("excluded", [])
    if name not in excluded:
        excluded.append(name)
    session["excluded"] = excluded

    return search()

@app.route("/clear")
def clear():
    session["excluded"] = []
    return search()

if __name__ == "__main__":
    import webbrowser
    webbrowser.open("http://127.0.0.1:5000")
    app.run()