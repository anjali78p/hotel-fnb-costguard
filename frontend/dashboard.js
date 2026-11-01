// Same-origin by default (FastAPI serves this folder). Set API_BASE if the API runs elsewhere.
const API_BASE = "";
const $ = s => document.querySelector(s);
const inr = n => n == null ? "–" : "₹" + Number(n).toLocaleString("en-IN", {maximumFractionDigits: 2});
const esc = v => String(v ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const charts = {};
let page = "overview", checkTab = "voids";

function qs(extra = {}) {
  const p = new URLSearchParams();
  const f = {date_from: $("#f-from").value, date_to: $("#f-to").value, outlet: $("#f-outlet").value, ...extra};
  Object.entries(f).forEach(([k, v]) => v && p.set(k, v));
  return p.toString() ? "?" + p : "";
}
async function api(path, extra) {
  const r = await fetch(API_BASE + path + qs(extra));
  if (!r.ok) throw new Error(`${path} returned ${r.status}`);
  return r.json();
}
function chart(id, type, labels, datasets, opts = {}) {
  charts[id]?.destroy();
  const el = document.getElementById(id);
  if (!el) return;
  charts[id] = new Chart(el, {type, data: {labels, datasets}, options: {responsive: true, ...opts}});
}
const COL = ["#0f5c54", "#b7791f", "#b3261e", "#4d7ea8", "#7a5c99"];
const card = (l, v, s = "", cls = "") => `<div class="card ${cls}"><div class="l">${esc(l)}</div><div class="v">${v}</div><div class="s">${esc(s)}</div></div>`;

function table(rows, cols) {
  if (!rows.length) return `<div class="empty">No records for these filters. Clear the filters or widen the date range.</div>`;
  const head = cols.map(c => `<th class="${c.n ? "n" : ""}">${esc(c.l)}</th>`).join("");
  const body = rows.map(r => "<tr>" + cols.map(c => {
    const raw = c.f ? c.f(r) : esc(r[c.k]);
    return `<td class="${c.n ? "n" : ""}">${raw === "" || raw == null || raw === "null" ? "–" : raw}</td>`;
  }).join("") + "</tr>").join("");
  return `<div class="wrap"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}
const flags = r => [
  r.missing_reason && `<span class="b">No reason</span>`,
  r.approval_issue && `<span class="b">Approval ${esc(r.approval_status)}</span>`,
  r.above_limit && `<span class="b">Above limit</span>`,
  r.high_value && `<span class="b amber">High value</span>`
].filter(Boolean).join("") || `<span class="b ok">Clear</span>`;
const amt = k => r => inr(r[k]);

const COLS = {
  voids: [{k: "check_id", l: "Check"}, {k: "business_date", l: "Date"}, {k: "outlet", l: "Outlet"}, {l: "Amount", n: 1, f: amt("void_amount")}, {k: "reason", l: "Reason"}, {k: "voided_by", l: "Voided by"}, {k: "approved_by", l: "Approver"}, {k: "remarks", l: "Remarks"}, {l: "Review flags", f: flags}],
  discounts: [{k: "check_id", l: "Check"}, {k: "business_date", l: "Date"}, {k: "outlet", l: "Outlet"}, {l: "Original", n: 1, f: amt("original_amount")}, {l: "Discount", n: 1, f: amt("discount_amount")}, {l: "Disc %", n: 1, f: r => r.discount_pct == null ? "–" : r.discount_pct + "%"}, {k: "reason", l: "Reason"}, {k: "entered_by", l: "Entered by"}, {k: "approved_by", l: "Approver"}, {l: "Review flags", f: flags}],
  nc: [{k: "check_id", l: "Check"}, {k: "business_date", l: "Date"}, {k: "outlet", l: "Outlet"}, {k: "reference_type", l: "Reference"}, {k: "reference_id", l: "Ref ID"}, {l: "NC value", n: 1, f: amt("nc_amount")}, {k: "reason", l: "Reason"}, {k: "approved_by", l: "Approver"}, {l: "Review flags", f: flags}],
  amenities: [{k: "check_id", l: "Check"}, {k: "business_date", l: "Date"}, {k: "room_or_event_ref", l: "Room / event"}, {k: "amenity_type", l: "Amenity"}, {k: "outlet", l: "Outlet"}, {k: "quantity", l: "Qty", n: 1}, {l: "Value", n: 1, f: amt("amount")}, {k: "reason", l: "Purpose"}, {k: "approved_by", l: "Approver"}, {l: "Review flags", f: flags}]
};

const pages = {
  async overview() {
    const [d, b] = await Promise.all([api("/api/dashboard"), api("/api/banquets")]);
    setFresh(d.data_freshness);
    const c = d.nc_amenities_combined;
    $("#page").innerHTML = `<h2>Overview</h2><p class="lead">Cost, stock and transaction controls for the selected period.</p>
      <div class="cards">
        ${card("Void checks", inr(d.voids.amount), d.voids.count + " unique checks", "warn")}
        ${card("Discounts", inr(d.discounts.amount), d.discounts.count + " checks, avg " + d.discounts.avg_discount_pct + "%", "warn")}
        ${card("NC value", inr(d.nc.amount), d.nc.count + " checks", "warn")}
        ${card("Amenities", inr(d.amenities.amount), d.amenities.count + " checks", "warn")}
        ${card("Stock variance", inr(d.stock_variance_value), "Positive = shortage", d.stock_variance_value > 0 ? "bad" : "")}
        ${card("Banquet gross profit", inr(d.banquet_gross_profit), b.kpi.count + " events")}
      </div>
      <div class="note">${esc(d.note)} NC + amenities combined: ${inr(c.combined_total)} (overlap of ${inr(c.overlap_value)} removed).</div>
      <div class="grid2">
        <div class="box"><h3>Transaction categories (may overlap)</h3><canvas id="c1"></canvas></div>
        <div class="box"><h3>Banquet gross profit by event</h3><canvas id="c2"></canvas></div>
      </div>`;
    chart("c1", "bar", ["Voids", "Discounts", "NC", "Amenities"], [{data: [d.voids.amount, d.discounts.amount, d.nc.amount, d.amenities.amount], backgroundColor: COL}], {plugins: {legend: {display: false}}});
    chart("c2", "bar", b.rows.map(r => r.event_id), [{data: b.rows.map(r => r.gross_profit), backgroundColor: b.rows.map(r => r.gross_profit < 0 ? "#b3261e" : "#0f5c54")}], {plugins: {legend: {display: false}}});
  },

  async checks() {
    const [v, d, n, a] = await Promise.all([api("/api/voids"), api("/api/discounts"), api("/api/nc-checks"), api("/api/amenities")]);
    setFresh(v.kpi.data_freshness);
    const data = {voids: v, discounts: d, nc: n, amenities: a};
    const exc = x => x.rows.filter(r => r.missing_reason || r.approval_issue || r.above_limit || r.high_value).length;
    const names = {voids: "Void checks", discounts: "Discount checks", nc: "NC checks", amenities: "Amenities checks"};
    const sub = {voids: x => `${x.kpi.count} unique, ${x.meta.duplicates_excluded} duplicate excluded`, discounts: x => `${x.kpi.count} unique, avg ${x.kpi.avg_discount_pct}%, limit ${x.kpi.limit_pct}%`, nc: x => `${x.kpi.count} unique`, amenities: x => `${x.kpi.count} unique`};
    $("#page").innerHTML = `<h2>Checks &amp; Revenue Control</h2>
      <p class="lead">Flags mark records for review against policy. They do not mean misconduct.</p>
      <div class="cards">${Object.keys(data).map(k => card(names[k], inr(data[k].kpi.amount), sub[k](data[k]) + " | " + exc(data[k]) + " to review", exc(data[k]) ? "warn" : "")).join("")}</div>
      <div class="note">Categories can overlap (for example an amenity also booked as NC), so do not add the four totals together.</div>
      <div class="grid2"><div class="box"><h3>Amount by outlet and category</h3><canvas id="c3"></canvas></div>
        <div class="box"><h3>Void reasons</h3><canvas id="c4"></canvas></div></div>
      <div class="tabs" id="ctabs">${Object.keys(data).map(k => `<button data-t="${k}" class="${k === checkTab ? "on" : ""}">${names[k]}</button>`).join("")}</div>
      <div id="ctable"></div>`;
    const outlets = [...new Set(Object.values(data).flatMap(x => x.rows.map(r => r.outlet)))];
    const key = {voids: "void_amount", discounts: "discount_amount", nc: "nc_amount", amenities: "amount"};
    chart("c3", "bar", outlets, Object.keys(data).map((k, i) => ({label: names[k], backgroundColor: COL[i],
      data: outlets.map(o => data[k].rows.filter(r => r.outlet === o).reduce((s, r) => s + r[key[k]], 0))})), {scales: {x: {stacked: true}, y: {stacked: true}}});
    const reasons = {};
    v.rows.forEach(r => { const k = r.reason || "(missing)"; reasons[k] = (reasons[k] || 0) + r.void_amount; });
    chart("c4", "bar", Object.keys(reasons), [{data: Object.values(reasons), backgroundColor: "#0f5c54"}], {indexAxis: "y", plugins: {legend: {display: false}}});
    const show = () => { $("#ctable").innerHTML = table(data[checkTab].rows, COLS[checkTab]); };
    show();
    $("#ctabs").onclick = e => { const t = e.target.dataset.t; if (!t) return; checkTab = t;
      document.querySelectorAll("#ctabs button").forEach(b => b.classList.toggle("on", b.dataset.t === t)); show(); };
  },

  async inventory() {
    const d = await api("/api/inventory");
    setFresh(d.kpi.data_freshness);
    const vt = r => r.variance_type === "shortage" ? `<span class="b">Shortage</span>` : r.variance_type === "surplus" ? `<span class="b amber">Surplus</span>` : `<span class="b ok">Matches</span>`;
    $("#page").innerHTML = `<h2>Inventory</h2><p class="lead">${esc(d.meta.sign_convention)}.</p>
      <div class="cards">${card("Items with variance", d.kpi.count, "of " + d.meta.total_rows + " lines")}${card("Net variance value", inr(d.kpi.amount), "Positive = shortage", d.kpi.amount > 0 ? "bad" : "")}</div>` +
      table(d.rows, [{k: "business_date", l: "Date"}, {k: "item_name", l: "Item"}, {k: "outlet", l: "Outlet"}, {k: "expected_closing", l: "Expected", n: 1}, {k: "book_closing_qty", l: "Book", n: 1}, {k: "physical_count", l: "Physical", n: 1}, {k: "variance_qty", l: "Variance qty", n: 1}, {l: "Variance value", n: 1, f: amt("variance_value")}, {l: "Status", f: vt}]);
  },

  async banquets() {
    const d = await api("/api/banquets");
    setFresh(d.kpi.data_freshness);
    $("#page").innerHTML = `<h2>Banquet profitability</h2><p class="lead">Gross profit = net revenue minus food, beverage and other direct costs.</p>
      <div class="cards">${card("Total gross profit", inr(d.kpi.amount), d.kpi.count + " events")}</div>
      <div class="box" style="margin-bottom:16px"><h3>Margin % by event</h3><canvas id="c5"></canvas></div>` +
      table(d.rows, [{k: "event_id", l: "Event"}, {k: "event_name", l: "Name"}, {k: "event_date", l: "Date"}, {k: "covers", l: "Covers", n: 1}, {l: "Net revenue", n: 1, f: amt("net_revenue")}, {l: "Gross profit", n: 1, f: amt("gross_profit")}, {l: "Margin", n: 1, f: r => r.margin_pct == null ? "n/a (no revenue)" : r.margin_pct + "%"}]);
    chart("c5", "bar", d.rows.map(r => r.event_id), [{data: d.rows.map(r => r.margin_pct), backgroundColor: d.rows.map(r => (r.margin_pct ?? -1) < 0 ? "#b3261e" : "#0f5c54")}], {plugins: {legend: {display: false}}});
  },

  async alerts() {
    const pr = $("#pri")?.value || "";
    const d = await api("/api/alerts", pr ? {priority: pr} : {});
    $("#page").innerHTML = `<h2>Corrective actions</h2><p class="lead">${esc(d.note)}</p>
      <div class="filters"><label>Priority <select id="pri"><option value="">All</option><option>High</option><option>Medium</option><option>Low</option></select></label><span class="fresh">${d.count} items</span></div>` +
      table(d.alerts, [{l: "Priority", f: r => `<span class="b ${r.priority === "High" ? "" : r.priority === "Medium" ? "amber" : "ok"}">${esc(r.priority)}</span>`}, {k: "category", l: "Category"}, {k: "reference", l: "Reference"}, {k: "evidence", l: "Evidence"}, {k: "likely_cause", l: "Likely cause"}, {k: "owner", l: "Owner"}, {k: "recommended_action", l: "Recommended action"}, {k: "status", l: "Status"}]);
    $("#pri").value = pr;
    $("#pri").onchange = () => pages.alerts().catch(showErr);
  }
};

function setFresh(t) { $("#fresh").textContent = t ? "Data as of " + new Date(t).toLocaleString("en-IN") : ""; }
function showErr(e) { const m = $("#msg"); m.hidden = false; m.textContent = "Could not load data: " + e.message + ". Check that the API is running."; }
async function render() {
  $("#msg").hidden = true;
  try { await pages[page](); } catch (e) { showErr(e); }
}
$("#nav").onclick = e => { const p = e.target.dataset.page; if (!p) return; page = p;
  document.querySelectorAll("#nav button").forEach(b => b.classList.toggle("on", b.dataset.page === p)); render(); };
$("#apply").onclick = render;
$("#reset").onclick = () => { ["#f-from", "#f-to", "#f-outlet"].forEach(s => $(s).value = ""); render(); };
render();
