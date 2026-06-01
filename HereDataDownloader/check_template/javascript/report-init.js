/* Bootstrap: event handlers, hash state, and JSON loading. */
(function() {
    "use strict";
    var R = window.ReportApp;

    function start(config) {
        var state = {
            rows: [],
            statusFilter: "all",
            query: "",
            sort: {key: null, dir: 1}
        };

        function writeHash() {
            var parts = [];
            if (state.statusFilter && state.statusFilter !== "all") parts.push("status=" + encodeURIComponent(state.statusFilter));
            if (state.query) parts.push("q=" + encodeURIComponent(state.query));
            if (state.sort.key) parts.push("sort=" + encodeURIComponent(state.sort.key) + (state.sort.dir < 0 ? ":desc" : ":asc"));
            var newHash = parts.length ? "#" + parts.join("&") : "";
            if (newHash !== window.location.hash) {
                try {
                    history.replaceState(null, "", window.location.pathname + window.location.search + newHash);
                } catch (e) { /* non-critical */ }
            }
        }

        function refresh() {
            R.renderTable(state, config);
            R.renderChips(state);
            writeHash();
        }

        function attachEvents() {
            var search = document.getElementById("searchInput");
            if (search) {
                search.addEventListener("input", function(e) {
                    state.query = e.target.value;
                    refresh();
                });
            }
            var chips = document.getElementById("statusChips");
            if (chips) {
                chips.addEventListener("click", function(e) {
                    var btn = e.target.closest(".chip");
                    if (!btn) return;
                    state.statusFilter = btn.getAttribute("data-status");
                    refresh();
                });
            }
            var ths = document.querySelectorAll("thead th.sortable");
            ths.forEach(function(th) {
                var key = th.getAttribute("data-key");
                function activate() {
                    if (state.sort.key === key) state.sort.dir = -state.sort.dir;
                    else { state.sort.key = key; state.sort.dir = 1; }
                    refresh();
                }
                th.addEventListener("click", activate);
                th.addEventListener("keydown", function(e) {
                    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); activate(); }
                });
            });
        }

        function applyHashToState() {
            var h = R.parseHash();
            if (h.status) state.statusFilter = h.status;
            if (h.q) {
                state.query = h.q;
                var search = document.getElementById("searchInput");
                if (search) search.value = h.q;
            }
            if (h.sort) {
                var parts = h.sort.split(":");
                state.sort.key = parts[0] || null;
                state.sort.dir = parts[1] === "desc" ? -1 : 1;
            }
        }

        function bootstrap() {
            attachEvents();
            var url = typeof config.jsonFile === "function" ? config.jsonFile() : config.jsonFile;
            if (!url) return;
            window.jQuery.getJSON(url, function(json) {
                state.rows = config.flatten(json);
                if (config.setHeader) config.setHeader(json);
                applyHashToState();
                refresh();
            }).fail(function() {
                var body = document.getElementById("resultBody");
                if (body) body.innerHTML = "<tr><td colspan=\"99\"><div class=\"empty-state\">Failed to load " + R.escapeHtml(url) + "</div></td></tr>";
            });
        }

        if (window.jQuery) window.jQuery(bootstrap);
        else document.addEventListener("DOMContentLoaded", bootstrap);
    }

    R.start = start;
})();
