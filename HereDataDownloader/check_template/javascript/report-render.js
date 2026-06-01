/* Render, filter, sort, and search logic. */
(function() {
    "use strict";
    var R = window.ReportApp;

    function compareValues(a, b) {
        var an = parseFloat(a);
        var bn = parseFloat(b);
        var aNum = a !== "" && a != null && !isNaN(an);
        var bNum = b !== "" && b != null && !isNaN(bn);
        if (aNum && bNum) return an - bn;
        return String(a == null ? "" : a).localeCompare(String(b == null ? "" : b));
    }

    function renderCell(col, row) {
        if (col.render === "status") {
            var label = row.status || "—";
            return "<span class=\"status-badge status-" + row.statusKey + "\">" + R.escapeHtml(label) + "</span>";
        }
        if (col.render === "link") {
            var href = row[col.key];
            if (!href) return "";
            return "<a href=\"" + R.escapeHtml(href) + "\">Report</a>";
        }
        if (col.render === "size") {
            return R.escapeHtml(R.formatBytes(row[col.key]));
        }
        if (col.render === "delta") {
            var n = Number(row[col.key]);
            if (!isFinite(n)) return R.escapeHtml(row[col.key]);
            var cls = n > 0 ? "delta delta-pos" : n < 0 ? "delta delta-neg" : "delta delta-zero";
            var prefix = n > 0 ? "+" : "";
            return "<span class=\"" + cls + "\">" + prefix + n + "</span>";
        }
        return R.escapeHtml(row[col.key]);
    }

    function renderTable(state, config) {
        var filtered = state.rows.filter(function(row) { return passesFilters(state, config, row); });
        var sorted = filtered.slice();
        if (state.sort.key) {
            var key = state.sort.key;
            var dir = state.sort.dir;
            sorted.sort(function(a, b) { return compareValues(a[key], b[key]) * dir; });
        }

        var cols = config.columns;
        var body = document.getElementById("resultBody");
        if (!sorted.length) {
            body.innerHTML = "<tr><td colspan=\"" + cols.length + "\"><div class=\"empty-state\">No rows match the current filters.</div></td></tr>";
        } else {
            var html = "";
            for (var r = 0; r < sorted.length; r++) {
                var row = sorted[r];
                html += "<tr class=\"status-row-" + row.statusKey + "\">";
                for (var c = 0; c < cols.length; c++) {
                    var col = cols[c];
                    if (col.group && !state.sort.key) {
                        if (r > 0 && sorted[r - 1][col.key] === row[col.key]) continue;
                        var span = 1;
                        while (r + span < sorted.length && sorted[r + span][col.key] === row[col.key]) { span++; }
                        html += "<td class=\"data-category\"" + (span > 1 ? " rowspan=\"" + span + "\"" : "") + ">" + R.escapeHtml(row[col.key]) + "</td>";
                    } else {
                        var clsAttr = col.cellClass ? " class=\"" + col.cellClass + "\"" : "";
                        html += "<td" + clsAttr + ">" + renderCell(col, row) + "</td>";
                    }
                }
                html += "</tr>";
            }
            body.innerHTML = html;
        }

        var counter = document.getElementById("rowCounter");
        if (counter) {
            counter.textContent = sorted.length === state.rows.length
                ? sorted.length + " row" + (sorted.length === 1 ? "" : "s")
                : sorted.length + " of " + state.rows.length + " rows";
        }

        var ths = document.querySelectorAll("thead th.sortable");
        ths.forEach(function(th) {
            var k = th.getAttribute("data-key");
            if (state.sort.key === k) th.setAttribute("aria-sort", state.sort.dir < 0 ? "descending" : "ascending");
            else th.removeAttribute("aria-sort");
        });
    }

    function passesFilters(state, config, row) {
        if (state.statusFilter !== "all" && row.statusKey !== state.statusFilter) return false;
        if (state.query) {
            var q = state.query.toLowerCase();
            var keys = config.searchKeys || Object.keys(row);
            var hay = "";
            for (var i = 0; i < keys.length; i++) {
                var v = row[keys[i]];
                if (v != null) hay += " " + v;
            }
            if (hay.toLowerCase().indexOf(q) === -1) return false;
        }
        return true;
    }

    function renderChips(state) {
        var container = document.getElementById("statusChips");
        if (!container) return;
        var counts = {all: state.rows.length};
        R.STATUS_FILTERS.forEach(function(f) { if (f.key !== "all") counts[f.key] = 0; });
        state.rows.forEach(function(row) { if (counts[row.statusKey] != null) counts[row.statusKey] += 1; });
        container.innerHTML = R.STATUS_FILTERS.map(function(f) {
            var active = state.statusFilter === f.key;
            return "<button type=\"button\" class=\"chip\" data-status=\"" + f.key + "\" aria-pressed=\"" + (active ? "true" : "false") + "\">"
                + R.escapeHtml(f.label)
                + " <span class=\"count\">" + (counts[f.key] || 0) + "</span>"
                + "</button>";
        }).join("");
    }

    R.renderTable = renderTable;
    R.renderChips = renderChips;
})();
