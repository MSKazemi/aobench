"""Static-site renderer for the AOBench leaderboard.

Jinja2 is preferred but not required.  When Jinja2 is unavailable the module
falls back to a plain f-string implementation that produces equivalent HTML.
"""

from __future__ import annotations

from pathlib import Path

try:
    from jinja2 import Template as _JinjaTemplate
    _JINJA2_AVAILABLE = True
except ImportError:
    _JINJA2_AVAILABLE = False

# ---------------------------------------------------------------------------
# Jinja2 template (used when Jinja2 is installed)
# ---------------------------------------------------------------------------

LEADERBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>AOBench Leaderboard</title>
<style>
body { font-family: monospace; max-width: 900px; margin: auto; padding: 2em; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
th { background: #f0f0f0; }
tr:nth-child(even) { background: #fafafa; }
</style>
</head>
<body>
<h1>AOBench Leaderboard</h1>
<p>Generated: {{ generated_at }}</p>
<table>
<tr>{% for col in columns %}<th>{{ col }}</th>{% endfor %}</tr>
{% for row in entries %}
<tr>
  <td>{{ loop.index }}</td>
  <td>{{ row.model_id }}</td>
  <td>{{ '%.4f' % (row.clear_score or 0) }}</td>
  <td>{{ '%.4f' % (row.E or 0) }}</td>
  <td>{{ '%.4f' % (row.A or 0) }}</td>
  <td>{{ '%.4f' % (row.R or 0) }}</td>
  <td>{{ row.n_tasks }}</td>
</tr>
{% endfor %}
</table>
</body>
</html>
"""

_COLUMNS = ["#", "Model", "CLEAR", "E", "A", "R", "N tasks"]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_leaderboard_html(leaderboard_response, output_path: Path) -> Path:
    """Render leaderboard to an HTML file.

    Parameters
    ----------
    leaderboard_response:
        A ``LeaderboardResponse`` (or any object with ``generated_at`` and
        ``entries`` attributes).
    output_path:
        Destination path for the HTML file.  Parent directories are created
        automatically.

    Returns
    -------
    Path
        The resolved path of the written file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    html = _render_html(leaderboard_response)
    output_path.write_text(html, encoding="utf-8")
    return output_path


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _render_html(leaderboard_response) -> str:
    """Return rendered HTML string."""
    if _JINJA2_AVAILABLE:
        return _render_with_jinja2(leaderboard_response)
    return _render_with_fstrings(leaderboard_response)


def _render_with_jinja2(leaderboard_response) -> str:
    template = _JinjaTemplate(LEADERBOARD_TEMPLATE)
    return template.render(
        generated_at=leaderboard_response.generated_at,
        columns=_COLUMNS,
        entries=leaderboard_response.entries,
    )


def _fmt(value) -> str:
    """Format an optional float to 4 decimal places."""
    return f"{value:.4f}" if value is not None else "0.0000"


def _render_with_fstrings(leaderboard_response) -> str:
    """Minimal HTML renderer using only f-strings (no Jinja2 dependency)."""
    header_cells = "".join(f"<th>{col}</th>" for col in _COLUMNS)

    row_cells_list = []
    for i, row in enumerate(leaderboard_response.entries, start=1):
        row_cells_list.append(
            f"<tr>"
            f"<td>{i}</td>"
            f"<td>{_escape(row.model_id)}</td>"
            f"<td>{_fmt(row.clear_score)}</td>"
            f"<td>{_fmt(row.E)}</td>"
            f"<td>{_fmt(row.A)}</td>"
            f"<td>{_fmt(row.R)}</td>"
            f"<td>{row.n_tasks}</td>"
            f"</tr>"
        )
    rows_html = "\n".join(row_cells_list)

    return (
        "<!DOCTYPE html>\n"
        "<html>\n"
        "<head><title>AOBench Leaderboard</title>\n"
        "<style>\n"
        "body { font-family: monospace; max-width: 900px; margin: auto; padding: 2em; }\n"
        "table { border-collapse: collapse; width: 100%; }\n"
        "th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }\n"
        "th { background: #f0f0f0; }\n"
        "tr:nth-child(even) { background: #fafafa; }\n"
        "</style>\n"
        "</head>\n"
        "<body>\n"
        "<h1>AOBench Leaderboard</h1>\n"
        f"<p>Generated: {_escape(leaderboard_response.generated_at)}</p>\n"
        "<table>\n"
        f"<tr>{header_cells}</tr>\n"
        f"{rows_html}\n"
        "</table>\n"
        "</body>\n"
        "</html>\n"
    )


def _escape(text: str) -> str:
    """Minimal HTML escaping."""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
    )
