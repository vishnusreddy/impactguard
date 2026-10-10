import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  ArrowUpRight,
  ArrowRight,
  ArrowLeft,
  Check,
  ChevronDown,
  ChevronRight,
  Command,
  Download,
  ExternalLink,
  GitBranch,
  Layers,
  LayoutDashboard,
  Link2,
  Loader2,
  Play,
  Plus,
  RotateCcw,
  Search,
  ShieldCheck,
  Sparkles,
  Terminal,
  TriangleAlert,
  X,
  CheckCircle2,
  Clock,
  SlidersHorizontal,
  Workflow,
  Zap,
} from "lucide-react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from "recharts";
import "./style.css";
const money = (n, decimals = 0) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(n || 0);
const pct = (n) => `${((n || 0) * 100).toFixed(1)}%`;
const scenarios = [
  {
    id: "banking",
    name: "Unbacked bank credits",
    description:
      "Failed transfers are marked successful and credited without settlement.",
    icon: Layers,
  },
  {
    id: "checkout",
    name: "Checkout regression",
    description: "A payment redirect release breaks Safari + PayPal.",
    icon: GitBranch,
  },
  {
    id: "promotion",
    name: "Promotion stacking",
    description: "Two discounts combine and erase contribution margin.",
    icon: Layers,
  },
  {
    id: "delivery",
    name: "Delivery delays",
    description: "Late deliveries correlate with fewer repeat purchases.",
    icon: Workflow,
  },
];
async function api(path, body) {
  const r = await fetch(
    "/api/" + path,
    body === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
  );
  const d = await r.json();
  if (!r.ok) throw Error(d.error || "Request failed");
  return d;
}
function App() {
  const [data, setData] = useState(null),
    [view, setView] = useState("overview"),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [demo, setDemo] = useState(false),
    [toast, setToast] = useState(""),
    [investigation, setInvestigation] = useState(null),
    [query, setQuery] = useState(""),
    [period, setPeriod] = useState("hour"),
    [selectedId, setSelectedId] = useState(null),
    [sort, setSort] = useState("priority"),
    [github, setGithub] = useState(null),
    [repoInput, setRepoInput] = useState(""),
    [expandedCommit, setExpandedCommit] = useState(null),
    [statusFilter, setStatusFilter] = useState("all"),
    [severityFilter, setSeverityFilter] = useState("all");
  useEffect(() => {
    api("github")
      .then(setGithub)
      .catch(() => {});
    api("dashboard")
      .then(setData)
      .catch((e) => setError(e.message));
    const t = setInterval(
      () =>
        api("dashboard")
          .then(setData)
          .catch(() => {}),
      5000,
    );
    return () => clearInterval(t);
  }, []);
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "instant" });
  }, [view]);
  useEffect(() => {
    if (toast) {
      const t = setTimeout(() => setToast(""), 4500);
      return () => clearTimeout(t);
    }
  }, [toast]);
  async function mutate(path, body, message) {
    setBusy(true);
    setError("");
    try {
      const d = await api(path, body);
      setData(d);
      if (message) setToast(message);
      return d;
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function launch(id) {
    const d = await mutate(
      "scenarios",
      { scenario: id },
      "Scenario launched. Evidence is ready.",
    );
    if (d) {
      setDemo(false);
      setInvestigation(null);
      setSelectedId(null);
      setView(id === "banking" ? "banking" : "overview");
    }
  }
  async function explain() {
    setBusy(true);
    try {
      setInvestigation(await api("investigate", { finding_id: f.id }));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function exportReport() {
    try {
      const d = await api("export" + (f ? "?finding_id=" + f.id : ""));
      const url = URL.createObjectURL(
        new Blob([JSON.stringify(d, null, 2)], { type: "application/json" }),
      );
      const a = document.createElement("a");
      a.href = url;
      a.download = "impactguard-incident-report.json";
      a.click();
      URL.revokeObjectURL(url);
      setToast("Incident report exported");
    } catch (e) {
      setError(e.message);
    }
  }
  const f =
      (view === "investigation" && selectedId
        ? data?.history.find((x) => x.id === selectedId)
        : null) || data?.finding,
    active = data?.status === "active";
  const nav = [
    ["overview", LayoutDashboard, "Business issues"],
    ["incidents", Activity, "Incidents"],
    ["changes", GitBranch, "Releases"],
    ["commits", Command, "Commit intelligence"],
    ["banking", Layers, "Reconciliation"],
    ["graph", Workflow, "Impact graph"],
    ["sources", Link2, "Data sources"],
    ["audit", Clock, "Activity log"],
  ];
  return (
    <div className="app">
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setView("overview");
          }}
        >
          <span className="brand-icon">
            <ShieldCheck size={22} />
          </span>
          ImpactGuard<span className="brand-dot">.</span>
        </a>
        <button className="workspace">
          <span className="avatar">A</span>
          <span>
            luma-goods<small>local / development</small>
          </span>
          <ChevronDown size={14} />
        </button>
        <div className="nav-label">PROJECT</div>
        <nav>
          {nav.map(([id, Icon, label]) => (
            <button
              key={id}
              className={view === id ? "selected" : ""}
              onClick={() => setView(id)}
            >
              <Icon size={18} />
              {label}
              {id === "incidents" && active && (
                <span className="nav-count">1</span>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="monitor">
            <span className={active ? "status-dot red-dot" : "status-dot"} />
            Demo telemetry ready
            <small>
              {data?.event_count?.toLocaleString() || "…"} synthetic events
              processed
            </small>
          </div>
          <button className="help-link" onClick={() => setView("sources")}>
            <Terminal size={16} />
            Developer quickstart
            <ArrowUpRight size={15} />
          </button>
          <div className="user">
            <span className="avatar light">YO</span>
            <span>
              Demo operator<small>Local environment</small>
            </span>
            <span className="tiny-tag">DEMO</span>
          </div>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <ChevronRight size={13} />{" "}
            <strong>
              {view === "investigation"
                ? "Investigation"
                : nav.find((n) => n[0] === view)?.[2]}
            </strong>
          </div>
          <div className="top-actions">
            <span className="demo-label">LOCAL DEMO</span>
            <button
              className="icon-button"
              aria-label="Open demo controls"
              onClick={() => setDemo(true)}
            >
              <SlidersHorizontal size={18} />
            </button>
            <span className="avatar small">YO</span>
          </div>
        </header>
        <div className="content">
          {error && (
            <div className="error" role="alert">
              {error}
              <button onClick={() => setError("")} aria-label="Dismiss error">
                <X size={16} />
              </button>
            </div>
          )}
          {!data ? (
            <div className="loading">
              <Loader2 className="spin" />
              Preparing business telemetry…
            </div>
          ) : (
            <>
              {view === "overview" && (
                <>
                  <div className="issue-head">
                    <div>
                      <div className="data-tags">
                        <span>SHOPIFY SELLER DEMO</span>
                        <span className="dark-tag">
                          {data.event_count.toLocaleString()} EVENTS
                        </span>
                      </div>
                      <h1>Business issues</h1>
                      <p>
                        Regressions linked to releases, customer segments, and
                        financial exposure.
                      </p>
                    </div>
                    <div className="issue-filters">
                      <label>
                        Environment
                        <select value="local" aria-label="Environment">
                          <option value="local">Local demo</option>
                        </select>
                      </label>
                      <label>
                        Sort by
                        <select
                          aria-label="Sort issues"
                          value={sort}
                          onChange={(e) => setSort(e.target.value)}
                        >
                          <option value="priority">Priority</option>
                          <option value="name">Issue name</option>
                        </select>
                      </label>
                      <label>
                        Search issues
                        <div className="filter-search">
                          <Search size={14} />
                          <input
                            aria-label="Search business issues"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            placeholder="e.g. checkout, coupon"
                          />
                        </div>
                      </label>
                    </div>
                  </div>
                  <section
                    className={
                      "summary-strip " +
                      (active ? "regression-state" : "healthy-state")
                    }
                  >
                    <div>
                      <small>Open issues</small>
                      <strong>
                        {active ? 1 : 0}
                        <em> / 4 monitored journeys</em>
                      </strong>
                    </div>
                    <div>
                      <small>Demo cohort revenue</small>
                      <strong>{money(data.metrics.revenue)}</strong>
                    </div>
                    <div>
                      <small>Projected exposure</small>
                      <strong className={active ? "risk-text" : ""}>
                        {active
                          ? money(f.exposure, f.scenario === "banking" ? 2 : 0)
                          : "$0"}
                        <em>{active ? " / " + f.unit : " active"}</em>
                      </strong>
                    </div>
                    <div className="summary-health">
                      <small>Current environment status</small>
                      <div>
                        <span
                          className={"status-dot " + (active ? "red-dot" : "")}
                        />
                        {active
                          ? "Business regression detected"
                          : data.status === "recovered"
                            ? "Recovery verified"
                            : "No active regressions"}
                      </div>
                      <span>
                        Synthetic telemetry. No production systems connected.
                      </span>
                    </div>
                  </section>
                  <div className="issue-toolbar">
                    <div className="issue-tabs">
                      <button className="active">
                        All journeys <span>3</span>
                      </button>
                      <button onClick={() => setView("incidents")}>
                        Investigations <span>{data.history.length}</span>
                      </button>
                    </div>
                    <button
                      className="button primary"
                      onClick={() => setDemo(true)}
                    >
                      <Play size={13} />
                      Run scenario
                    </button>
                  </div>
                  <div className="seller-context">
                    <strong>Luma Goods</strong>
                    <span>Independent Shopify seller</span>
                    <span>
                      Impact projections: 120 checkout starts/day × $82 order
                      value
                    </span>
                  </div>
                  {active && data.scenario === "banking" && (
                    <div className="bank-alert">
                      <TriangleAlert size={18} />
                      <strong>
                        Settlement mismatch:{" "}
                        {money(f.exposure, f.scenario === "banking" ? 2 : 0)} in
                        unbacked credits
                      </strong>
                      <button
                        className="text-button"
                        onClick={() => setView("banking")}
                      >
                        Open reconciliation <ArrowRight size={14} />
                      </button>
                    </div>
                  )}
                  <div className="issue-grid">
                    {scenarios
                      .filter((s) => s.id !== "banking")
                      .filter((s) => {
                        const item = data.history.find(
                          (x) => x.scenario === s.id,
                        );
                        return [
                          s.name,
                          s.description,
                          item?.title,
                          item?.segment,
                          item?.cause,
                          item?.commit_sha,
                          s.id === "promotion" ? "coupons" : "",
                        ]
                          .join(" ")
                          .toLowerCase()
                          .includes(query.toLowerCase());
                      })
                      .sort((a, b) =>
                        sort === "name"
                          ? a.name.localeCompare(b.name)
                          : (data.history.find((x) => x.scenario === b.id)
                              ?.status === "active"
                              ? 1
                              : 0) -
                            (data.history.find((x) => x.scenario === a.id)
                              ?.status === "active"
                              ? 1
                              : 0),
                      )
                      .map((s, i) => {
                        const finding = data.history.find(
                          (x) => x.scenario === s.id,
                        );
                        const running = finding?.status === "active";
                        return (
                          <section className="issue-evidence-card" key={s.id}>
                            <div className="issue-card-header">
                              <span className="issue-rank">{i + 1}</span>
                              <div>
                                <div className="category-line">
                                  <span className="category-label">
                                    {s.id === "checkout"
                                      ? "PAYMENTS"
                                      : s.id === "promotion"
                                        ? "PROMOTIONS"
                                        : "CUSTOMER RETENTION"}
                                  </span>
                                  <span
                                    className={
                                      "issue-state " +
                                      (running
                                        ? "issue-open"
                                        : finding
                                          ? "issue-resolved"
                                          : "")
                                    }
                                  >
                                    {finding
                                      ? finding.status === "active"
                                        ? "OPEN"
                                        : "RESOLVED"
                                      : "READY"}
                                  </span>
                                </div>
                                <h2>{finding?.title || s.name}</h2>
                              </div>
                            </div>
                            <p className="issue-card-description">
                              {finding
                                ? finding.summary.split(". ")[0] + "."
                                : s.description}
                            </p>
                            <div className="impact-number">
                              {finding ? money(finding.exposure) : "—"}
                              <small>
                                {finding
                                  ? " / " + finding.unit
                                  : " awaiting scenario"}
                              </small>
                            </div>
                            <div className="issue-impact-label">
                              {s.id === "promotion"
                                ? "Negative contribution margin"
                                : s.id === "delivery"
                                  ? "Annual retention scenario"
                                  : "Projected revenue exposure"}
                            </div>
                            <div className="sample-meta">
                              <span>
                                {finding
                                  ? finding.sample_size.toLocaleString() +
                                    " sessions"
                                  : "No incident evaluated"}
                              </span>
                              <span>
                                {finding
                                  ? Math.round(finding.score * 100) +
                                    "/100 correlation"
                                  : "Synthetic demo"}
                              </span>
                            </div>
                            <div className="card-evidence">
                              <div className="evidence-heading">
                                {finding
                                  ? "OBSERVED SIGNALS"
                                  : "DETECTION TARGETS"}
                              </div>
                              {(finding
                                ? finding.evidence
                                : [
                                    {
                                      label: "Metric",
                                      value:
                                        s.id === "checkout"
                                          ? "Checkout conversion"
                                          : s.id === "promotion"
                                            ? "Order contribution margin"
                                            : "30-day repeat purchase",
                                    },
                                    {
                                      label: "Segment",
                                      value:
                                        s.id === "checkout"
                                          ? "Safari / PayPal"
                                          : s.id === "promotion"
                                            ? "WELCOME20 + SUMMER25"
                                            : ">5-day delivery delay",
                                    },
                                    {
                                      label: "Change",
                                      value:
                                        s.id === "checkout"
                                          ? "Payment redirect release"
                                          : s.id === "promotion"
                                            ? "Coupon combination rules"
                                            : "Carrier routing update",
                                    },
                                  ]
                              ).map((e) => (
                                <div className="compact-evidence" key={e.label}>
                                  <span>{e.label}</span>
                                  <strong>{e.value}</strong>
                                </div>
                              ))}
                            </div>
                            <div className="commit-snippet">
                              <div>
                                <GitBranch size={13} />
                                <span>
                                  {finding?.cause || "No release correlated"}
                                </span>
                                {finding && (
                                  <code>{finding.commit_sha?.slice(0, 7)}</code>
                                )}
                              </div>
                              <p>
                                {finding?.commits?.[0]?.message ||
                                  "Run this scenario to inspect the candidate commit and diff."}
                              </p>
                              {finding?.commits?.[0] && (
                                <code className="file-path">
                                  {finding.commits[0].files[0].filename}
                                </code>
                              )}
                            </div>
                            <div className="issue-card-footer">
                              <span>
                                {finding
                                  ? `${finding.status === "recovered" ? "Resolved" : "Detected"} · ${new Date(finding.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`
                                  : "Not evaluated"}
                              </span>
                              <button
                                className="text-button"
                                disabled={!finding && active}
                                onClick={() => {
                                  if (finding) {
                                    setSelectedId(finding.id);
                                    setInvestigation(null);
                                    setView("investigation");
                                  } else launch(s.id);
                                }}
                              >
                                {finding ? "Open issue" : "Run scenario"}
                                <ArrowRight size={13} />
                              </button>
                            </div>
                          </section>
                        );
                      })}
                  </div>
                  <div className="overview-grid">
                    <section className="panel chart-panel">
                      <div className="panel-head">
                        <div>
                          <h2>Checkout conversion</h2>
                          <p>Measured from persisted session events</p>
                        </div>
                        <select
                          aria-label="Chart metric"
                          value={period}
                          onChange={(e) => setPeriod(e.target.value)}
                        >
                          <option value="hour">Conversion</option>
                          <option value="revenue">Revenue</option>
                        </select>
                      </div>
                      <div className="chart-legend">
                        <span>
                          <i style={{ background: "#3161b9" }} />
                          {period === "hour"
                            ? "Observed conversion"
                            : "Observed revenue"}
                        </span>
                        {period === "hour" && (
                          <span>
                            <i className="dashed" />
                            Historical baseline
                          </span>
                        )}
                        <span className="chart-note">
                          2-hour synthetic replay
                        </span>
                      </div>
                      <div className="chart">
                        <ResponsiveContainer width="100%" height="100%">
                          <AreaChart
                            data={data.series}
                            margin={{ top: 15, right: 20, left: 0, bottom: 0 }}
                          >
                            <CartesianGrid stroke="#e4e7eb" vertical={false} />
                            <XAxis
                              dataKey="time"
                              tickLine={false}
                              axisLine={false}
                              minTickGap={38}
                              tick={{ fontSize: 11, fill: "#7a8290" }}
                            />
                            <YAxis
                              domain={
                                period === "hour" ? [40, 90] : ["auto", "auto"]
                              }
                              tickFormatter={(v) =>
                                period === "hour"
                                  ? v + "%"
                                  : "$" + (v / 1000).toFixed(0) + "k"
                              }
                              axisLine={false}
                              tickLine={false}
                              tick={{ fontSize: 11, fill: "#7a8290" }}
                            />
                            <Tooltip
                              formatter={(v) =>
                                period === "hour" ? v + "%" : money(v)
                              }
                              contentStyle={{
                                border: "1px solid #d4d9e0",
                                borderRadius: 4,
                                fontSize: 12,
                              }}
                            />
                            {period === "hour" && (
                              <Line
                                type="monotone"
                                dataKey="expected"
                                name="Baseline"
                                stroke="#8d96a3"
                                strokeDasharray="4 4"
                                dot={false}
                              />
                            )}
                            <Area
                              type="monotone"
                              dataKey={period === "hour" ? "actual" : "revenue"}
                              name={
                                period === "hour" ? "Conversion" : "Revenue"
                              }
                              stroke="#3266bb"
                              strokeWidth={2}
                              fill="#3266bb"
                              fillOpacity={0.06}
                            />
                          </AreaChart>
                        </ResponsiveContainer>
                      </div>
                      <div className="chart-footer">
                        <span>
                          {data.metrics.n.toLocaleString()} current sessions
                        </span>
                        <span>30,000 baseline sessions</span>
                      </div>
                    </section>
                    <section className="panel recent-changes">
                      <div className="panel-head">
                        <div>
                          <h2>Recent changes</h2>
                          <p>Releases evaluated in this workspace</p>
                        </div>
                        <button
                          className="text-button"
                          onClick={() => setView("changes")}
                        >
                          View all
                        </button>
                      </div>
                      {data.deployments.length ? (
                        data.deployments.slice(0, 4).map((d) => (
                          <div className="recent-change" key={d.id}>
                            <GitBranch size={16} />
                            <div>
                              <strong>{d.version}</strong>
                              <p>{JSON.parse(d.components).join(", ")}</p>
                            </div>
                            <span>
                              {new Date(d.timestamp).toLocaleTimeString([], {
                                hour: "2-digit",
                                minute: "2-digit",
                              })}
                            </span>
                          </div>
                        ))
                      ) : (
                        <p className="no-changes">
                          No deployments yet. Run a scenario to record a
                          release.
                        </p>
                      )}
                      <div className="integration-note">
                        <span className="status-dot" />
                        GitHub adapter available{" "}
                        <button onClick={() => setView("commits")}>
                          View commit intelligence <ArrowUpRight size={12} />
                        </button>
                      </div>
                    </section>
                  </div>
                  <div className="bottom-note">
                    Local demo · persisted SQLite events · heuristic commit
                    ranking
                    <span>
                      Last refreshed{" "}
                      {new Date(data.updated_at).toLocaleTimeString()}
                    </span>
                  </div>
                </>
              )}
              {view === "investigation" && f && (
                <>
                  <button
                    className="text-button back"
                    onClick={() => setView("overview")}
                  >
                    <ArrowLeft size={15} />
                    Business issues
                  </button>
                  <div className="page-head">
                    <div>
                      <div className="eyebrow">
                        INVESTIGATION / {f.id.slice(0, 8).toUpperCase()}
                      </div>
                      <h1>{f.title}</h1>
                      <p>
                        Evidence, suspect commits, and remediation for this
                        regression.
                      </p>
                    </div>
                    <button className="button" onClick={exportReport}>
                      <Download size={15} />
                      Export report
                    </button>
                  </div>
                  <div
                    className={
                      "investigation-stats " +
                      (f.status === "active"
                        ? "active-incident"
                        : "resolved-incident")
                    }
                  >
                    <div>
                      <small>
                        {f.scenario === "banking"
                          ? "UNBACKED LEDGER CREDITS"
                          : "PROJECTED EXPOSURE"}
                      </small>
                      <strong>
                        {money(f.exposure, f.scenario === "banking" ? 2 : 0)}
                        <em>
                          {f.unit === "unbacked" ? " unbacked" : " / " + f.unit}
                        </em>
                      </strong>
                    </div>
                    <div>
                      <small>AFFECTED SEGMENT</small>
                      <strong>{f.segment}</strong>
                    </div>
                    <div>
                      <small>LIKELY CHANGE</small>
                      <strong className="mono">{f.cause}</strong>
                    </div>
                    <div>
                      <small>CORRELATION SCORE</small>
                      <strong>
                        {Math.round(f.score * 100)}
                        <em> / 100</em>
                      </strong>
                    </div>
                  </div>
                  <div className="invest-grid">
                    <div>
                      <section className="panel investigation-panel">
                        <div className="panel-head">
                          <div>
                            <h2>
                              <Sparkles size={18} />
                              Analysis
                            </h2>
                            <p>
                              {investigation?.provider || f.reasoning_provider}{" "}
                              · Evidence-based explanation
                            </p>
                          </div>
                          <button
                            className="button"
                            disabled={busy}
                            onClick={explain}
                          >
                            {busy ? (
                              <Loader2 size={15} className="spin" />
                            ) : (
                              <Sparkles size={15} />
                            )}
                            Investigate
                          </button>
                        </div>
                        <p className="briefing">
                          {investigation?.summary || f.summary}
                        </p>
                        {investigation?.recommended_verification && (
                          <p className="verification">
                            Next verification:{" "}
                            {investigation.recommended_verification}
                          </p>
                        )}
                        <div className="confidence-note">
                          <ShieldCheck size={15} />
                          {f.confidence_label}. Review supporting evidence
                          before acting.
                        </div>
                      </section>
                      <section className="panel investigation-panel">
                        <h2>Supporting evidence</h2>
                        {f.evidence.map((e, i) => (
                          <div className="evidence" key={e.label}>
                            <span className="evidence-number">0{i + 1}</span>
                            <div>
                              <small>{e.label}</small>
                              <strong>{e.value}</strong>
                              <p>{e.detail}</p>
                            </div>
                            <CheckCircle2 size={17} color="#477a62" />
                          </div>
                        ))}
                      </section>
                      {f.segments.length > 0 && (
                        <section className="panel investigation-panel">
                          <h2>Segment comparison</h2>
                          <table>
                            <thead>
                              <tr>
                                <th>Customer segment</th>
                                <th>Baseline</th>
                                <th>Current</th>
                                <th>Sessions</th>
                              </tr>
                            </thead>
                            <tbody>
                              {f.segments.map((s) => (
                                <tr key={s.name}>
                                  <td>{s.name}</td>
                                  <td>{pct(s.baseline)}</td>
                                  <td
                                    className={
                                      s.baseline - s.actual > 0.1
                                        ? "risk-text"
                                        : ""
                                    }
                                  >
                                    {pct(s.actual)}
                                  </td>
                                  <td>{s.sessions.toLocaleString()}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </section>
                      )}
                      <section className="panel investigation-panel">
                        <div className="panel-head">
                          <div>
                            <h2>Suspect commits</h2>
                            <p>
                              Ranked by timing, affected files, and diff
                              relevance. Synthetic fixtures.
                            </p>
                          </div>
                        </div>
                        {f.commits?.slice(0, 3).map((c, i) => (
                          <div className="suspect-commit" key={c.sha}>
                            <div className="suspect-title">
                              <code>{c.sha.slice(0, 7)}</code>
                              <strong>{c.message}</strong>
                              <span>{Math.round(c.score * 100)}/100</span>
                            </div>
                            <div className="commit-reasons">
                              {c.reasons.map((r) => (
                                <span key={r}>{r}</span>
                              ))}
                            </div>
                            {i === 0 && <Diff commit={c} />}
                          </div>
                        ))}
                      </section>
                      <section className="panel investigation-panel">
                        <h2>
                          {f.scenario === "banking"
                            ? "Reconciliation amount"
                            : "Dollar impact methodology"}
                        </h2>
                        <code className="formula">{f.formula}</code>
                        <p className="muted">
                          {f.scenario === "banking"
                            ? "The engine sums ledger credits without settlement evidence. This is an observed accounting discrepancy in the synthetic records. Recovery records explicit reversals."
                            : "The engine calculates this value from observed counts and explicit seller assumptions. It projects exposure if the pattern persists. It does not measure realized loss or proven savings."}
                        </p>
                      </section>
                    </div>
                    <div>
                      <section
                        className={
                          "action-panel " +
                          (f.status === "recovered" ? "resolved" : "")
                        }
                      >
                        <div className="eyebrow">
                          {f.status === "recovered"
                            ? "RECOVERY VERIFIED"
                            : "RECOMMENDED RESPONSE"}
                        </div>
                        <span className="action-icon">
                          {f.status === "recovered" ? (
                            <CheckCircle2 size={30} />
                          ) : (
                            <RotateCcw size={30} />
                          )}
                        </span>
                        <h2>
                          {f.status === "recovered"
                            ? f.scenario === "banking"
                              ? "Ledger reconciliation verified"
                              : "Healthy outcomes restored"
                            : f.action}
                        </h2>
                        <p>
                          {f.status === "recovered"
                            ? f.recovery_summary
                            : "Apply the fix to the synthetic generator, then verify the affected business metric."}
                        </p>
                        <button
                          className="button primary full"
                          disabled={busy || f.status === "recovered"}
                          onClick={() =>
                            mutate(
                              "actions",
                              { action: "recover", finding_id: f.id },
                              f.scenario === "banking"
                                ? "Reconciliation complete. Corrective reversals recorded."
                                : "Recovery verified on 6,000 new simulated sessions.",
                            )
                          }
                        >
                          {busy ? (
                            <Loader2 size={16} className="spin" />
                          ) : f.status === "recovered" ? (
                            <Check size={16} />
                          ) : (
                            <RotateCcw size={16} />
                          )}{" "}
                          {f.status === "recovered"
                            ? "Recovery confirmed"
                            : "Simulate remediation"}
                        </button>
                        <small>
                          Demo action. No production system changes.
                        </small>
                        <button
                          className="text-button"
                          disabled={busy}
                          onClick={() =>
                            mutate(
                              "actions",
                              { action: "assign", finding_id: f.id },
                              "Incident assigned to you",
                            )
                          }
                        >
                          {f.owner === "You" ? (
                            <Check size={15} />
                          ) : (
                            <Plus size={15} />
                          )}{" "}
                          {f.owner === "You"
                            ? "Assigned to you"
                            : "Assign to me"}
                        </button>
                      </section>
                      <section className="panel timeline-panel">
                        <h2>Incident timeline</h2>
                        <p className="muted">
                          Synthetic event chronology · UTC
                        </p>
                        <div className="timeline">
                          {f.timeline.map((t) => (
                            <div key={t.time}>
                              <span className="timeline-dot" />
                              <small>{t.time}</small>
                              <strong>{t.title}</strong>
                              <p>{t.detail}</p>
                            </div>
                          ))}
                          {f.status === "recovered" && (
                            <div>
                              <span className="timeline-dot green-dot" />
                              <small>NOW</small>
                              <strong>Recovery verified</strong>
                              <p>New traffic confirms healthy outcomes</p>
                            </div>
                          )}
                        </div>
                      </section>
                    </div>
                  </div>
                </>
              )}
              {view === "incidents" && (
                <>
                  <PageHead
                    eyebrow="INVESTIGATIONS"
                    title="Incidents"
                    description="Every business regression, with its evidence and response."
                  />
                  <div className="search">
                    <Search size={18} />
                    <input
                      aria-label="Search incidents"
                      placeholder="Search by incident, segment, or change…"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                    />
                  </div>
                  <div className="incident-filters">
                    <select
                      aria-label="Incident status"
                      value={statusFilter}
                      onChange={(e) => setStatusFilter(e.target.value)}
                    >
                      <option value="all">All statuses</option>
                      <option value="active">Open</option>
                      <option value="recovered">Resolved</option>
                    </select>
                    <select
                      aria-label="Incident severity"
                      value={severityFilter}
                      onChange={(e) => setSeverityFilter(e.target.value)}
                    >
                      <option value="all">All severities</option>
                      <option value="critical">Critical</option>
                      <option value="high">High</option>
                    </select>
                  </div>
                  {data.history
                    .filter(
                      (x) =>
                        (statusFilter === "all" || x.status === statusFilter) &&
                        (severityFilter === "all" ||
                          x.severity === severityFilter),
                    )
                    .filter((x) =>
                      (x.title + x.segment + x.cause)
                        .toLowerCase()
                        .includes(query.toLowerCase()),
                    )
                    .map((x) => (
                      <IncidentCard
                        key={x.id}
                        finding={x}
                        onClick={() => {
                          if (x.id === f?.id) setView("investigation");
                          else
                            setToast(
                              "This historical incident is included in the activity log.",
                            );
                        }}
                      />
                    ))}
                  {data.history.length === 0 && (
                    <Empty
                      title="Your first investigation starts with a change"
                      description="Run a demo scenario to generate customer events and detect a business regression."
                      action={() => setDemo(true)}
                    />
                  )}
                </>
              )}
              {view === "changes" && (
                <>
                  <PageHead
                    eyebrow="CHANGE INTELLIGENCE"
                    title="Every change has a business footprint"
                    description="Connect releases and business decisions to the customer journeys they affect."
                  />
                  <div className="panel table-panel">
                    <table>
                      <thead>
                        <tr>
                          <th>Change</th>
                          <th>Components</th>
                          <th>Recorded</th>
                          <th>Monitoring</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.deployments.map((d) => (
                          <tr key={d.id}>
                            <td>
                              <GitBranch size={15} />{" "}
                              <strong>{d.version}</strong>
                            </td>
                            <td>{JSON.parse(d.components).join(", ")}</td>
                            <td>
                              {new Date(d.timestamp).toLocaleTimeString()}
                            </td>
                            <td>
                              <span className="badge green">Evaluated</span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {!data.deployments.length && (
                      <Empty
                        title="No changes recorded yet"
                        description="Introduce a release, promotion, or routing change using the scenario controls."
                        action={() => setDemo(true)}
                      />
                    )}
                  </div>
                  <div className="info-block">
                    <h2>Watch the outcome, beyond the deploy</h2>
                    <p>
                      ImpactGuard maps the changed component to a customer
                      journey. Temporal proximity, segment overlap and
                      supporting telemetry rank candidate causes. These scores
                      support investigation and do not establish causality.
                    </p>
                  </div>
                </>
              )}
              {view === "graph" && (
                <>
                  <PageHead
                    eyebrow="BUSINESS IMPACT GRAPH"
                    title="The path from a change to a dollar"
                    description="A shared map for engineering, operations, and the business."
                  />
                  <section className="panel graph-panel">
                    {[
                      {
                        name: "Checkout",
                        nodes: [
                          "checkout-service",
                          "Payment redirect",
                          "Checkout conversion",
                          "Order revenue",
                        ],
                      },
                      {
                        name: "Profitability",
                        nodes: [
                          "Promotion rules",
                          "Discount application",
                          "Contribution margin",
                          "Order profit",
                        ],
                      },
                      {
                        name: "Retention",
                        nodes: [
                          "Carrier routing",
                          "Delivery experience",
                          "Repeat purchase",
                          "Customer revenue",
                        ],
                      },
                    ].map((g, i) => (
                      <div className="graph-journey" key={g.name}>
                        <div className="eyebrow">
                          0{i + 1} / {g.name.toUpperCase()}
                        </div>
                        <div className="graph-chain">
                          {g.nodes.map((node, j) => (
                            <React.Fragment key={node}>
                              <div
                                className={
                                  "graph-node " + (j === 3 ? "outcome" : "")
                                }
                              >
                                <small>
                                  {
                                    [
                                      "CHANGE",
                                      "CUSTOMER JOURNEY",
                                      "BUSINESS METRIC",
                                      "DOLLAR OUTCOME",
                                    ][j]
                                  }
                                </small>
                                <strong>{node}</strong>
                                {j === 3 ? (
                                  <ArrowUpRight size={18} />
                                ) : (
                                  <span className="node-dot" />
                                )}
                              </div>
                              {j < 3 && (
                                <ArrowRight size={22} className="graph-arrow" />
                              )}
                            </React.Fragment>
                          ))}
                        </div>
                      </div>
                    ))}
                  </section>
                  <div className="info-block">
                    <h2>Built for decisions across teams</h2>
                    <p>
                      A declared relationship graph narrows which metrics to
                      inspect after a change. The current graph is explicit
                      configuration. Automatic graph discovery belongs on the
                      production roadmap.
                    </p>
                  </div>
                </>
              )}
              {view === "banking" && (
                <>
                  <div className="page-head">
                    <div>
                      <div className="eyebrow">
                        BANKING / SETTLEMENT RECONCILIATION
                      </div>
                      <h1>Unbacked credits</h1>
                      <p>
                        Compare application success, bank settlement evidence,
                        and ledger postings.
                      </p>
                    </div>
                    <button
                      className="button primary"
                      disabled={busy || active}
                      onClick={() => launch("banking")}
                    >
                      <Play size={14} />
                      Run banking scenario
                    </button>
                  </div>
                  <section
                    className={
                      "summary-strip " +
                      (data.banking.mismatches
                        ? "regression-state"
                        : "healthy-state")
                    }
                  >
                    <div>
                      <small>Transactions evaluated</small>
                      <strong>
                        {data.banking.total?.toLocaleString() || "0"}
                      </strong>
                    </div>
                    <div>
                      <small>Status mismatches</small>
                      <strong
                        className={data.banking.mismatches ? "risk-text" : ""}
                      >
                        {data.banking.mismatches || 0}
                      </strong>
                    </div>
                    <div>
                      <small>Unbacked credits</small>
                      <strong>{money(data.banking.exposure, 2)}</strong>
                    </div>
                    <div>
                      <small>Corrective reversal entries</small>
                      <strong>{data.banking.reversals}</strong>
                    </div>
                  </section>
                  <div
                    className={
                      "bank-status " +
                      (data.banking.mismatches ? "bank-danger" : "bank-healthy")
                    }
                  >
                    {data.banking.mismatches ? (
                      <TriangleAlert size={18} />
                    ) : (
                      <CheckCircle2 size={18} />
                    )}
                    <strong>
                      {data.banking.mismatches
                        ? "Reconciliation failed. App success does not match settlement."
                        : data.banking.total
                          ? "Reconciled. Original postings and reversal entries retained."
                          : "No banking scenario evaluated yet."}
                    </strong>
                    {data.history.find((x) => x.scenario === "banking") && (
                      <button
                        className="text-button"
                        onClick={() => {
                          setSelectedId(
                            data.history.find((x) => x.scenario === "banking")
                              .id,
                          );
                          setView("investigation");
                        }}
                      >
                        Investigate suspect commit <ArrowRight size={14} />
                      </button>
                    )}
                  </div>
                  <section className="panel table-panel">
                    <div className="panel-head">
                      <h2>Settlement evidence</h2>
                      <span className="muted">
                        Synthetic bank records · sample of affected transfers
                      </span>
                    </div>
                    <table>
                      <thead>
                        <tr>
                          <th>Transaction</th>
                          <th>Bank status</th>
                          <th>App status</th>
                          <th>Amount</th>
                          <th>Reconciliation</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.banking.transactions.map((t) => (
                          <tr key={t.id}>
                            <td>
                              <code>{t.id}</code>
                            </td>
                            <td>
                              <span className="badge orange">
                                {t.bank_status}
                              </span>
                            </td>
                            <td>
                              <span
                                className={
                                  "badge " +
                                  (t.app_status === "success"
                                    ? "orange"
                                    : "green")
                                }
                              >
                                {t.app_status}
                              </span>
                            </td>
                            <td>{money(t.amount, 2)}</td>
                            <td>
                              <span
                                className={
                                  "badge " +
                                  (t.app_status === "success"
                                    ? "orange"
                                    : "green")
                                }
                              >
                                {t.app_status === "success"
                                  ? "Unbacked credit"
                                  : "Reversed"}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {!data.banking.total && (
                      <div className="no-changes">
                        Run the banking scenario to generate a buggy callback
                        mapper, bank settlement records, and actual ledger
                        entries.
                      </div>
                    )}
                  </section>
                  <div className="info-block">
                    <h2>Settlement evidence is the accounting boundary</h2>
                    <p>
                      A success flag in an application is not cash settlement.
                      The detector checks the bank outcome against the ledger.
                      The demo fix records a reversal for each erroneous credit
                      and keeps the original posting. Production systems would
                      also verify cash movement and apply approved accounting
                      controls.
                    </p>
                  </div>
                </>
              )}
              {view === "commits" && (
                <>
                  <PageHead
                    eyebrow="CODE INTELLIGENCE"
                    title="Commit intelligence"
                    description="Inspect the code changes that could explain a business regression."
                  />
                  <section className="panel github-connect">
                    <div>
                      <h2>GitHub repository</h2>
                      <p>
                        {github?.connected
                          ? github.repo + " · read-only sync"
                          : "No repository connected. The demo below uses synthetic commit fixtures."}
                      </p>
                    </div>
                    <div className="connect-input">
                      <input
                        aria-label="GitHub repository"
                        placeholder="owner/repository"
                        value={repoInput}
                        onChange={(e) => setRepoInput(e.target.value)}
                      />
                      <button
                        className="button primary"
                        disabled={busy || !repoInput}
                        onClick={async () => {
                          setBusy(true);
                          try {
                            setGithub(
                              await api("github/connect", { repo: repoInput }),
                            );
                            setToast("Read-only commit sync complete");
                          } catch (e) {
                            setError(e.message);
                          } finally {
                            setBusy(false);
                          }
                        }}
                      >
                        {busy ? (
                          <Loader2 size={14} className="spin" />
                        ) : (
                          <Link2 size={14} />
                        )}
                        Connect
                      </button>
                    </div>
                  </section>
                  <div className="repo-disclosure">
                    {github?.connected
                      ? "Imported repository commits are shown below. They are not automatically associated with synthetic demo incidents."
                      : "Demo repository: acme/commerce-demo · synthetic commit metadata and diffs"}
                  </div>
                  <section className="panel commit-list">
                    {(github?.connected
                      ? github.commits
                      : f?.commits || []
                    ).map((c) => (
                      <div className="commit-list-item" key={c.sha}>
                        <button
                          className="commit-list-head"
                          onClick={() =>
                            setExpandedCommit(
                              expandedCommit === c.sha ? null : c.sha,
                            )
                          }
                        >
                          <GitBranch size={17} />
                          <code>{c.sha.slice(0, 7)}</code>
                          <div>
                            <strong>{c.message}</strong>
                            <small>
                              {c.author} ·{" "}
                              {new Date(c.timestamp).toLocaleString()}
                            </small>
                          </div>
                          {c.score !== undefined && (
                            <span className="score-label">
                              {Math.round(c.score * 100)}/100
                            </span>
                          )}
                          <ChevronDown size={15} />
                        </button>
                        {expandedCommit === c.sha && (
                          <div className="commit-detail">
                            {c.reasons && (
                              <div className="commit-reasons">
                                {c.reasons.map((r) => (
                                  <span key={r}>{r}</span>
                                ))}
                              </div>
                            )}
                            <Diff commit={c} />
                            {c.url && (
                              <a
                                className="text-button"
                                href={c.url}
                                target="_blank"
                                rel="noreferrer"
                              >
                                Open on GitHub <ExternalLink size={13} />
                              </a>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                    {!f && !github?.connected && (
                      <div className="no-commit-state">
                        <p>
                          Run any scenario to inspect ranked commits and their
                          diffs.
                        </p>
                        <button
                          className="button"
                          onClick={() => setDemo(true)}
                        >
                          Run scenario
                        </button>
                      </div>
                    )}
                  </section>
                  <div className="info-block">
                    <h2>How candidate ranking works</h2>
                    <p>
                      Timing contributes 30%, service file overlap 30%, relevant
                      diff terms 25%, and affected segment evidence 15%. A high
                      score indicates a plausible candidate for investigation.
                      Production attribution also needs a deployment-to-commit
                      mapping and a measured anomaly onset.
                    </p>
                  </div>
                </>
              )}
              {view === "sources" && (
                <>
                  <PageHead
                    eyebrow="DATA FOUNDATION"
                    title="One contract. A complete business picture."
                    description="The demo uses synthetic customer events. Production connectors can use the same ingestion boundary."
                  />
                  <div className="source-grid">
                    {[
                      [
                        "Event simulator",
                        "Connected",
                        "30 days of baseline data and controlled regression scenarios.",
                      ],
                      [
                        "Event ingestion API",
                        "Available",
                        "POST /api/events accepts and deduplicates unified events. External events are stored separately from demo analytics.",
                      ],
                      [
                        "Google Cloud",
                        "Not connected",
                        "Cloud Run, Pub/Sub, BigQuery and Vertex AI setup is prepared for your personal project.",
                      ],
                      [
                        "Commerce & support",
                        "Roadmap",
                        "Shopify, Stripe and support connectors are on the roadmap. A read-only GitHub adapter is available in Commit intelligence.",
                      ],
                    ].map(([title, status, desc]) => (
                      <div className="panel source-card" key={title}>
                        <span className="watch-icon">
                          <Link2 size={20} />
                        </span>
                        <span
                          className={
                            "badge " +
                            (status === "Connected" ? "green" : "neutral")
                          }
                        >
                          {status}
                        </span>
                        <h2>{title}</h2>
                        <p>{desc}</p>
                      </div>
                    ))}
                  </div>
                  <section className="panel code-panel">
                    <div className="panel-head">
                      <h2>Send your first event</h2>
                      <button
                        className="text-button"
                        onClick={() => {
                          navigator.clipboard.writeText(example);
                          setToast("Example copied");
                        }}
                      >
                        Copy example <Check size={15} />
                      </button>
                    </div>
                    <pre>{example}</pre>
                    <p className="muted">
                      Use a stable event_id for retry-safe ingestion. This local
                      endpoint is intended for demo use.
                    </p>
                  </section>
                </>
              )}
              {view === "audit" && (
                <>
                  <PageHead
                    eyebrow="ACCOUNTABILITY"
                    title="Activity log"
                    description="A persistent record of demo changes, detections, and operator actions."
                  />
                  <section className="panel audit-panel">
                    {data.audit.map((a, i) => (
                      <div className="audit-row" key={i}>
                        <span className="watch-icon">
                          {a.action.includes("remediation") ? (
                            <RotateCcw size={18} />
                          ) : (
                            <Activity size={18} />
                          )}
                        </span>
                        <div>
                          <strong>{a.action}</strong>
                          <p>{a.detail}</p>
                        </div>
                        <time>
                          {new Date(a.timestamp).toLocaleTimeString()}
                        </time>
                      </div>
                    ))}
                  </section>
                </>
              )}
            </>
          )}
        </div>
      </main>
      {demo && (
        <div className="modal-backdrop" onClick={() => setDemo(false)}>
          <section
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="demo-title"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="close icon-button"
              aria-label="Close scenario controls"
              onClick={() => setDemo(false)}
            >
              <X size={20} />
            </button>
            <div className="eyebrow">THE IMPACTGUARD DEMO</div>
            <h2 id="demo-title">
              Introduce a change.
              <br />
              Watch the business impact.
            </h2>
            <p>
              Generate real, persisted synthetic events. The engine measures the
              regression and calculates its exposure.
            </p>
            {scenarios.map((s) => (
              <button
                className="scenario-option"
                disabled={busy || active}
                key={s.id}
                onClick={() => launch(s.id)}
              >
                <span className="watch-icon">
                  <s.icon size={21} />
                </span>
                <span>
                  <strong>{s.name}</strong>
                  <small>{s.description}</small>
                </span>
                {busy ? (
                  <Loader2 size={18} className="spin" />
                ) : (
                  <ArrowUpRight size={18} />
                )}
              </button>
            ))}
            {active && (
              <p className="muted">
                Resolve the active incident or reset to run another scenario.
              </p>
            )}
            <button
              className="button full"
              disabled={busy}
              onClick={async () => {
                const d = await mutate(
                  "reset",
                  {},
                  "Demo reset to a healthy baseline",
                );
                if (d) {
                  setDemo(false);
                  setView("overview");
                  setInvestigation(null);
                }
              }}
            >
              <RotateCcw size={15} />
              Reset to healthy baseline
            </button>
            <small className="modal-disclosure">
              All data and actions are synthetic. No connected accounts are
              used.
            </small>
          </section>
        </div>
      )}
      {toast && (
        <div className="toast" role="status">
          <CheckCircle2 size={18} />
          {toast}
        </div>
      )}
    </div>
  );
}
function Metric({ title, value, suffix, detail, warn, icon: Icon }) {
  return (
    <div className={"metric " + (warn ? "metric-risk" : "")}>
      <div className="metric-label">
        {title}
        <Icon size={15} />
      </div>
      <div className="metric-value">
        {value}
        <small>{suffix}</small>
      </div>
      <div className="metric-detail">
        {warn && <span className="status-dot" />}
        {detail}
      </div>
    </div>
  );
}
function PageHead({ eyebrow, title, description }) {
  return (
    <div className="page-head">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
    </div>
  );
}
function Empty({ title, description, action }) {
  return (
    <div className="empty-state">
      <ShieldCheck size={28} />
      <div>
        <strong>{title}</strong>
        <p>{description}</p>
      </div>
      <button className="button" onClick={action}>
        Run scenario <Play size={14} />
      </button>
    </div>
  );
}
function IncidentCard({ finding: f, onClick }) {
  return (
    <button className="incident-card" onClick={onClick}>
      <span
        className={
          "incident-icon " + (f.status === "recovered" ? "green-icon" : "")
        }
      >
        {f.status === "recovered" ? (
          <CheckCircle2 size={23} />
        ) : (
          <TriangleAlert size={23} />
        )}
      </span>
      <div className="incident-main">
        <div className="incident-title">
          <span
            className={
              "badge " + (f.status === "recovered" ? "green" : "orange")
            }
          >
            {f.status === "recovered" ? "Recovered" : f.severity}
          </span>
          <strong>{f.title}</strong>
        </div>
        <p>
          <GitBranch size={13} />
          {f.cause}
          <span className="divider" /> {f.segment}
        </p>
      </div>
      <div className="incident-exposure">
        <strong>
          {money(f.exposure, f.scenario === "banking" ? 2 : 0)}
          <small>{f.unit === "unbacked" ? " unbacked" : " / " + f.unit}</small>
        </strong>
        <span>
          {f.scenario === "banking"
            ? "Observed reconciliation discrepancy"
            : `Projected ${f.scenario === "promotion" ? "margin" : "revenue"} exposure`}
        </span>
      </div>
      <span className="investigate-link">
        Investigate <ArrowUpRight size={16} />
      </span>
    </button>
  );
}
function Diff({ commit }) {
  return (
    <div className="diff-files">
      {commit.files.map((file) => (
        <div className="diff-file" key={file.filename}>
          <div className="diff-file-head">
            <code>{file.filename}</code>
            <span className="diff-add">+{file.additions}</span>
            <span className="diff-remove">−{file.deletions}</span>
          </div>
          <pre>
            {file.patch.split("\n").map((line, i) => (
              <span
                className={
                  line.startsWith("+")
                    ? "added"
                    : line.startsWith("-")
                      ? "removed"
                      : "context"
                }
                key={i}
              >
                {line + "\n"}
              </span>
            ))}
          </pre>
        </div>
      ))}
    </div>
  );
}
const example = `curl -X POST http://localhost:8080/api/events \\\n  -H 'Content-Type: application/json' \\\n  -d '{"event_id":"evt_001","timestamp":"2026-10-10T14:00:00Z",\n       "source":"checkout","event_type":"checkout_completed",\n       "session_id":"S001","browser":"Safari",\n       "payment_method":"PayPal","amount":82}'`;
createRoot(document.getElementById("root")).render(<App />);
