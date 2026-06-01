/* Core utilities for raw-data report templates. */
(function() {
    "use strict";

    var STATUS_FILTERS = [
        {key: "all", label: "All"},
        {key: "pass", label: "Pass"},
        {key: "warning", label: "Warning"},
        {key: "error", label: "Error"},
        {key: "not-ready", label: "Not ready"}
    ];

    function statusKey(raw) {
        if (raw == null) return "unknown";
        var s = String(raw).trim().toLowerCase();
        if (!s) return "unknown";
        if (s === "pass") return "pass";
        if (s === "warning") return "warning";
        if (s === "error") return "error";
        if (s === "not ready" || s === "not_ready" || s === "not-ready") return "not-ready";
        return "unknown";
    }

    function escapeHtml(value) {
        if (value == null) return "";
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\"/g, "&quot;")
            .replace(/`/g, "&#96;");
    }

    function parseHash() {
        var hash = (window.location.hash || "").replace(/^#/, "");
        if (!hash) return {};
        var out = {};
        hash.split("&").forEach(function(pair) {
            if (!pair) return;
            var idx = pair.indexOf("=");
            var k = decodeURIComponent(idx === -1 ? pair : pair.slice(0, idx));
            var v = idx === -1 ? "" : decodeURIComponent(pair.slice(idx + 1));
            out[k] = v;
        });
        return out;
    }

    function formatBytes(value) {
        var n = Number(value);
        if (!isFinite(n) || n === 0) return value == null || value === "" ? "" : String(value);
        var abs = Math.abs(n);
        var units = ["B", "KB", "MB", "GB", "TB"];
        var i = 0;
        while (abs >= 1024 && i < units.length - 1) { abs /= 1024; i++; }
        var sign = n < 0 ? "-" : "";
        return sign + abs.toFixed(abs >= 100 || i === 0 ? 0 : 1) + " " + units[i];
    }

    window.ReportApp = window.ReportApp || {};
    window.ReportApp.STATUS_FILTERS = STATUS_FILTERS;
    window.ReportApp.statusKey = statusKey;
    window.ReportApp.escapeHtml = escapeHtml;
    window.ReportApp.parseHash = parseHash;
    window.ReportApp.formatBytes = formatBytes;
})();
