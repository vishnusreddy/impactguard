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
      "Simulate a status mapping error that credits failed and pending transfers.",
    icon: Layers,
  },
  {
    id: "checkout",
    name: "Checkout regression",
    description:
      "Simulate failed checkout attempts in Safari sessions that use PayPal.",
    icon: GitBranch,
  },
  {
    id: "promotion",
    name: "Promotion stacking",
    description:
      "Simulate combined discounts that produce negative contribution margin.",
    icon: Layers,
  },
  {
    id: "delivery",
    name: "Delivery delays",
    description:
      "Compare repeat purchase rates for on-time and delayed deliveries.",
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
function reviewLabel(status) {
  return (
    {
      active: "Open",
      resolved: "Resolved",
      recovered: "Resolved",
      ignored: "Ignored",
      not_issue: "Not an issue",
      healthy: "Healthy",
    }[status] || status
  );
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
    [storeInput, setStoreInput] = useState(""),
    [propertyInput, setPropertyInput] = useState(""),
    [policyInput, setPolicyInput] = useState(""),
    [sourceAnalysis, setSourceAnalysis] = useState(null),
    [metricAssessment, setMetricAssessment] = useState(null),
    [businessContext, setBusinessContext] = useState(""),
    [sampleScenario, setSampleScenario] = useState("checkout"),
    [expandedCommit, setExpandedCommit] = useState(null),
    [statusFilter, setStatusFilter] = useState("all"),
    [severityFilter, setSeverityFilter] = useState("all"),
    [categoryFilter, setCategoryFilter] = useState("all"),
    [publicScenario, setPublicScenario] = useState("checkout");
  async function runMetricAssessment(sample) {
    setBusy(true);
    setError("");
    try {
      const result = await api("metrics/discover", {
        sample,
        business_context: businessContext,
      });
      setMetricAssessment(result);
      setToast("Metric assessment completed. Proposals require review.");
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  function renderMetricRefs(refs) {
    return (refs || [])
      .map((ref) => {
        const source = metricAssessment?.sources?.find((s) => s.id === ref.id);
        return source?.file
          ? `${source.repo}/${source.file}:${ref.line}`
          : source?.source || ref.id;
      })
      .join("; ");
  }
  useEffect(() => {
    api("github")
      .then((d) => {
        setGithub(d);
        setMetricAssessment(d.metric_assessment || null);
        setStoreInput(d.config?.shopify_store || "");
        setPropertyInput(d.config?.ga_property || "");
        setPolicyInput(d.policy || "");
      })
      .catch(() => {});
    api("dashboard?scenario=" + publicScenario)
      .then(setData)
      .catch((e) => setError(e.message));
    const t = setInterval(
      () =>
        api("dashboard?scenario=" + publicScenario)
          .then(setData)
          .catch(() => {}),
      5000,
    );
    return () => clearInterval(t);
  }, [publicScenario]);
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
    if (publicAccess) {
      setError("Owner access is required to change project data.");
      return;
    }
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
    if (publicAccess) {
      setPublicScenario(id);
      setDemo(false);
      setSelectedId(null);
      setInvestigation(null);
      setView(id === "banking" ? "banking" : "overview");
      return;
    }
    const d = await mutate(
      "scenarios",
      { scenario: id },
      "Scenario completed. The incident is available.",
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
      setInvestigation(
        await api("investigate", { finding_id: f.id, scenario: f.scenario }),
      );
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function exportReport() {
    try {
      const d = await api(
        "export?scenario=" + publicScenario + (f ? "&finding_id=" + f.id : ""),
      );
      const url = URL.createObjectURL(
        new Blob([JSON.stringify(d, null, 2)], { type: "application/json" }),
      );
      const a = document.createElement("a");
      a.href = url;
      a.download = "impactguard-incident-report.json";
      a.click();
      URL.revokeObjectURL(url);
      setToast("Incident report downloaded.");
    } catch (e) {
      setError(e.message);
    }
  }
  const f =
      (view === "investigation" && selectedId
        ? data?.history.find((x) => x.id === selectedId)
        : null) || data?.finding,
    active = data?.status === "active" && Boolean(f),
    attribution = investigation || f?.investigation,
    publicAccess = data?.deployment?.access === "public";
  const nav = [
    ["overview", LayoutDashboard, "Overview"],
    ["incidents", Activity, "Issues"],
    ["commits", Command, "Codebases"],
    ["sources", Link2, "Integrations"],
  ];
  async function connectionRequest(path, body) {
    if (publicAccess && path !== "integrations/collect") {
      setError(
        "Owner access is required for account connections and project settings.",
      );
      return;
    }
    setBusy(true);
    setError("");
    try {
      setGithub(await api(path, body));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
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
            luma-goods
            <small>
              {data?.deployment?.environment === "Cloud Run"
                ? publicAccess
                  ? "Cloud Run / public demo"
                  : "Cloud Run / owner"
                : "Local / development"}
            </small>
          </span>
          <ChevronDown size={14} />
        </button>
        <div className="nav-label">Project</div>
        <nav>
          {nav.map(([id, Icon, label]) => (
            <button
              key={id}
              className={view === id ? "selected" : ""}
              aria-label={label}
              title={label}
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
            Event data available
            <small>
              {data?.event_count?.toLocaleString() || "…"} synthetic events
              processed
            </small>
          </div>
          <button className="help-link" onClick={() => setView("sources")}>
            <Terminal size={16} />
            Ingestion API
            <ArrowUpRight size={15} />
          </button>
          <div className="user">
            <span className="avatar light">YO</span>
            <span>
              Demo operator
              <small>
                {data?.deployment?.environment || "Local"} environment
              </small>
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
                : nav.find((n) => n[0] === view)?.[2] ||
                  {
                    banking: "Reconciliation",
                    changes: "Releases",
                    graph: "Metric dependencies",
                    audit: "Audit log",
                  }[view]}
            </strong>
          </div>
          <div className="top-actions">
            <span className="demo-label">Sample data</span>
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
          {publicAccess && (
            <p className="public-notice">
              Public demo · generated data and cached Gemini analysis. Account
              connections and project changes require owner access.
            </p>
          )}
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
              Loading event data…
            </div>
          ) : (
            <>
              {view === "overview" && (
                <>
                  <div className="issue-head">
                    <div>
                      <div className="data-tags">
                        <span>Shopify demo</span>
                        <span className="dark-tag">
                          {data.event_count.toLocaleString()} events
                        </span>
                      </div>
                      <h1>Business regressions</h1>
                      <p>
                        Review metric regressions, affected segments, and
                        related code changes.
                      </p>
                    </div>
                    <div className="issue-filters">
                      <label>
                        Environment
                        <select value="local" aria-label="Environment">
                          <option value="local">
                            {data?.deployment?.environment || "Local"} demo
                          </option>
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
                            aria-label="Search regressions"
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
                      <small>Open incidents</small>
                      <strong>
                        {active ? 1 : 0}
                        <em> / 4 monitored metrics</em>
                      </strong>
                    </div>
                    <div>
                      <small>
                        {f?.scenario === "banking"
                          ? "Transactions evaluated"
                          : "Sample revenue"}
                      </small>
                      <strong>
                        {f?.scenario === "banking"
                          ? data.banking.total.toLocaleString()
                          : money(data.metrics.revenue)}
                      </strong>
                    </div>
                    <div>
                      <small>
                        {f?.scenario === "banking"
                          ? "Unbacked credits"
                          : "Estimated exposure"}
                      </small>
                      <strong className={active ? "risk-text" : ""}>
                        {f?.scenario === "banking"
                          ? money(data.banking.exposure, 2)
                          : active
                            ? money(f.exposure)
                            : "$0"}
                        <em>
                          {active && f.unit !== "unbacked"
                            ? " / " + f.unit
                            : null}
                        </em>
                      </strong>
                    </div>
                    <div className="summary-health">
                      <small>Incident status</small>
                      <div>
                        <span
                          className={"status-dot " + (active ? "red-dot" : "")}
                        />
                        {active
                          ? "Active incident"
                          : ["resolved", "recovered"].includes(data.status)
                            ? "Reviewed"
                            : data.status === "unassessed"
                              ? "AI assessment unavailable"
                              : data.status === "baseline"
                                ? "Baseline data; not assessed"
                                : "No active incidents"}
                      </div>
                      <span>
                        Synthetic data. No production integrations are
                        connected.
                      </span>
                    </div>
                  </section>
                  <div className="issue-toolbar">
                    <div className="issue-tabs">
                      <button className="active">
                        Metrics <span>3</span>
                      </button>
                      <button onClick={() => setView("incidents")}>
                        Incidents <span>{data.history.length}</span>
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
                    <span>Shopify seller example</span>
                    <span>
                      Estimate assumptions: 120 checkout starts/day × $82 order
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
                        const candidate = finding?.commits?.find(
                          (c) =>
                            c.sha ===
                            finding?.investigation?.suspect_commit_sha,
                        );
                        const running = finding?.status === "active";
                        return (
                          <section className="issue-evidence-card" key={s.id}>
                            <div className="issue-card-header">
                              <div className="category-line">
                                <span className="category-label">
                                  {s.id === "checkout"
                                    ? "Payments"
                                    : s.id === "promotion"
                                      ? "Promotions"
                                      : "Retention"}
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
                                      ? "Open"
                                      : finding.status === "recovered"
                                        ? "Resolved"
                                        : reviewLabel(finding.status)
                                    : "Not evaluated"}
                                </span>
                              </div>
                              <span className="issue-rank">{i + 1}</span>
                              <h2>{finding?.title || s.name}</h2>
                            </div>
                            <p className="issue-card-description">
                              {finding
                                ? s.id === "checkout"
                                  ? "Checkout completion fell for Safari customers paying with PayPal."
                                  : s.id === "promotion"
                                    ? `${finding.evidence[0].value} have negative contribution margin after coupon stacking.`
                                    : "Late deliveries correlate with lower 30-day repeat purchase rates."
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
                                  ? "Annual retention estimate"
                                  : "Estimated revenue exposure"}
                            </div>
                            <div className="sample-meta">
                              <span>
                                {finding
                                  ? finding.sample_size.toLocaleString() +
                                    " sessions"
                                  : "No incident recorded"}
                              </span>
                              <span>
                                {finding
                                  ? finding.detection_provider?.startsWith(
                                      "Vertex",
                                    )
                                    ? "AI decision"
                                    : "Unassessed"
                                  : "Synthetic data"}
                              </span>
                            </div>
                            <div className="card-evidence">
                              <div className="evidence-heading">
                                {finding
                                  ? "Observed results"
                                  : "Monitored metrics"}
                              </div>
                              {(finding
                                ? finding.evidence
                                : [
                                    {
                                      label: "Metric",
                                      value:
                                        s.id === "checkout"
                                          ? "Checkout completion rate"
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
                                  {finding?.cause || "No related release"}
                                </span>
                                {finding && (
                                  <code>{finding.commit_sha?.slice(0, 7)}</code>
                                )}
                              </div>
                              <p>
                                {candidate?.message ||
                                  "Run the scenario to evaluate related commits."}
                              </p>
                              {candidate && (
                                <code className="file-path">
                                  {candidate.files[0]?.filename}
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
                                {finding ? "View incident" : "Run scenario"}
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
                          <h2>Checkout completion rate</h2>
                          <p>Calculated from stored session events.</p>
                        </div>
                        <select
                          aria-label="Chart metric"
                          value={period}
                          onChange={(e) => setPeriod(e.target.value)}
                        >
                          <option value="hour">Completion rate</option>
                          <option value="revenue">Revenue</option>
                        </select>
                      </div>
                      <div className="chart-legend">
                        <span>
                          <i style={{ background: "#3161b9" }} />
                          {period === "hour"
                            ? "Observed completion rate"
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
                              tick={{ fontSize: 12, fill: "#697588" }}
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
                              tick={{ fontSize: 12, fill: "#697588" }}
                            />
                            <Tooltip
                              formatter={(v) =>
                                period === "hour" ? v + "%" : money(v)
                              }
                              contentStyle={{
                                border: "1px solid #d4d9e0",
                                borderRadius: 4,
                                fontSize: 13,
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
                                period === "hour"
                                  ? "Completion rate"
                                  : "Revenue"
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
                          <h2>Recent releases</h2>
                          <p>Releases recorded in this workspace.</p>
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
                          No releases recorded. Run a scenario to create a
                          release record.
                        </p>
                      )}
                      <div className="integration-note">
                        <span className="status-dot" />
                        GitHub import available{" "}
                        <button onClick={() => setView("commits")}>
                          View commit analysis <ArrowUpRight size={12} />
                        </button>
                      </div>
                    </section>
                  </div>
                  <div className="bottom-note">
                    {data?.deployment?.durable
                      ? "Cloud Run · durable checkpoints"
                      : "Local demo · SQLite state"}{" "}
                    · Gemini detection and attribution
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
                    Regressions
                  </button>
                  <div className="page-head">
                    <div>
                      <div className="eyebrow">
                        Incident {f.id.slice(0, 8).toUpperCase()}
                      </div>
                      <h1>{f.title}</h1>
                      <p>
                        Measurements, candidate commits, and review decisions
                        for this incident.
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
                          ? "Unbacked ledger credits"
                          : "Estimated exposure"}
                      </small>
                      <strong>
                        {money(f.exposure, f.scenario === "banking" ? 2 : 0)}
                        <em>
                          {f.unit === "unbacked" ? " unbacked" : " / " + f.unit}
                        </em>
                      </strong>
                    </div>
                    <div>
                      <small>Affected segment</small>
                      <strong>{f.segment}</strong>
                    </div>
                    <div>
                      <small>Candidate release</small>
                      <strong className="mono">{f.cause}</strong>
                    </div>
                    <div>
                      <small>AI code attribution</small>
                      <strong>
                        {attribution?.attribution_status ===
                        "validated_reference"
                          ? "Reference validated"
                          : "Pending"}
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
                              Provider:{" "}
                              {attribution?.provider || f.reasoning_provider}
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
                            Run analysis
                          </button>
                        </div>
                        <p className="briefing">
                          {attribution?.summary || f.summary}
                        </p>
                        {attribution?.classification && (
                          <p className="muted">
                            Classification:{" "}
                            {attribution.classification.replaceAll("_", " ")}
                          </p>
                        )}
                        {attribution?.limitation && (
                          <p className="muted">{attribution.limitation}</p>
                        )}
                        {attribution?.usage?.total_tokens && (
                          <p className="muted">
                            {attribution.cached
                              ? "Cached analysis"
                              : `${attribution.usage.total_tokens.toLocaleString()} tokens used`}
                          </p>
                        )}
                        {attribution?.recommended_verification && (
                          <p className="verification">
                            Verification step:{" "}
                            {attribution.recommended_verification}
                          </p>
                        )}
                        <div className="confidence-note">
                          <ShieldCheck size={15} />A validated code reference is
                          a candidate, not proof of causation. Review the
                          measurements before accepting a candidate cause.
                        </div>
                      </section>
                      <section className="panel investigation-panel">
                        <h2>LLM anomaly decision</h2>
                        <p className="muted">
                          {f.detection_provider || "Not assessed"}
                        </p>
                        <p>
                          {f.detection?.reason ||
                            "No Gemini decision is stored for this window."}
                        </p>
                        <p className="muted">
                          Evidence references:{" "}
                          {f.detection?.evidence_refs?.join(", ") || "None"}.
                          SQL measures outcomes; Gemini makes the decision.
                        </p>
                      </section>
                      {attribution?.attribution_status ===
                        "validated_reference" && (
                        <section className="panel investigation-panel">
                          <h2>AI candidate cause</h2>
                          <code>
                            {attribution.suspect_commit_sha.slice(0, 12)} ·{" "}
                            {attribution.file}:{attribution.line}
                          </code>
                          <p>{attribution.defect_explanation}</p>
                          <p className="muted">
                            The cited line exists in the supplied diff. This
                            does not establish causation.
                          </p>
                          <h3>Other commits</h3>
                          {attribution.ruled_out_commits?.map((c) => (
                            <p key={c.sha}>
                              <code>{c.sha.slice(0, 7)}</code> {c.reason}
                            </p>
                          ))}
                        </section>
                      )}
                      {attribution && (
                        <section className="panel investigation-panel">
                          <h2>Suggested fix and guard test</h2>
                          <p className="muted">
                            AI drafts for review. Never applied or executed.
                            Test compatibility has not been verified.
                          </p>
                          {attribution.suggested_fix_diff && (
                            <>
                              <h3>Suggested fix</h3>
                              <pre className="draft-diff">
                                {attribution.suggested_fix_diff}
                              </pre>
                            </>
                          )}
                          {attribution.guard_test_diff && (
                            <>
                              <h3>Guard test</h3>
                              <pre className="draft-diff">
                                {attribution.guard_test_diff}
                              </pre>
                            </>
                          )}
                          {attribution.draft_warnings?.map((w) => (
                            <p className="muted" key={w}>
                              {w}
                            </p>
                          ))}
                        </section>
                      )}
                      <section className="panel investigation-panel">
                        <h2>Measurements</h2>
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
                          <div className="table-scroll">
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
                          </div>
                        </section>
                      )}
                      <section className="panel investigation-panel">
                        <div className="panel-head">
                          <div>
                            <h2>Candidate commits</h2>
                            <p>
                              Gemini compares all eligible diffs. The heuristic
                              is retained only as an evaluation baseline.
                            </p>
                          </div>
                        </div>
                        {(attribution?.suspect_commit_sha
                          ? [...(f.commits || [])].sort(
                              (x, y) =>
                                Number(
                                  y.sha === attribution.suspect_commit_sha,
                                ) -
                                Number(
                                  x.sha === attribution.suspect_commit_sha,
                                ),
                            )
                          : f.commits || []
                        ).map((c, i) => (
                          <div
                            className="suspect-commit"
                            key={c.repo + ":" + c.sha}
                          >
                            <div className="suspect-title">
                              <code>{c.sha.slice(0, 7)}</code>
                              <strong>{c.message}</strong>
                              {c.sha === attribution?.suspect_commit_sha && (
                                <span className="badge neutral">
                                  AI candidate
                                </span>
                              )}
                            </div>
                            {(c.sha === attribution?.suspect_commit_sha ||
                              i === 0) && (
                              <Diff
                                commit={c}
                                highlight={
                                  attribution?.attribution_status ===
                                  "validated_reference"
                                    ? attribution
                                    : null
                                }
                              />
                            )}
                          </div>
                        ))}
                      </section>
                      <section className="panel investigation-panel">
                        <h2>
                          {f.scenario === "banking"
                            ? "Reconciliation amount"
                            : "Impact calculation"}
                        </h2>
                        <code className="formula">{f.formula}</code>
                        <p className="muted">
                          {f.scenario === "banking"
                            ? "The amount is the sum of synthetic ledger credits without confirmed settlement. Review actions preserve the original postings."
                            : "This estimate uses measured sample rates and configured seller volume. It assumes that the observed pattern persists. It does not represent realized loss or savings."}
                        </p>
                      </section>
                    </div>
                    <div>
                      <section className="action-panel">
                        <div className="eyebrow">Issue review</div>
                        <h2>Review the candidate cause</h2>
                        <p>
                          Current state:{" "}
                          {f.status === "active"
                            ? "Open"
                            : reviewLabel(f.status)}
                          . Review actions do not modify code, transactions, or
                          source measurements.
                        </p>
                        <p>
                          {f.classification?.replaceAll("_", " ") ||
                            "Unclassified"}
                          . {f.classification_basis}
                        </p>
                        <div className="review-actions">
                          {[
                            ["resolve", "Mark resolved"],
                            ["ignore", "Ignore"],
                            ["not_issue", "Not an issue"],
                            ["reopen", "Reopen"],
                          ].map(([action, label]) => (
                            <button
                              key={action}
                              className="button secondary"
                              disabled={busy || publicAccess}
                              onClick={() =>
                                mutate(
                                  "actions",
                                  { action, finding_id: f.id },
                                  "Review state updated. Evidence retained.",
                                )
                              }
                            >
                              {label}
                            </button>
                          ))}
                        </div>
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
                          {["resolved", "recovered"].includes(f.status) && (
                            <div>
                              <span className="timeline-dot green-dot" />
                              <small>
                                {f.recovered_at
                                  ? new Date(f.recovered_at)
                                      .toISOString()
                                      .slice(11, 16)
                                  : "Reviewed"}
                              </small>
                              <strong>Marked resolved</strong>
                              <p>
                                Manual review completed for the synthetic data.
                              </p>
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
                    eyebrow="Incident history"
                    title="Issues"
                    description="Review measurements, issue classifications, and candidate causes."
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
                      aria-label="Issue category"
                      value={categoryFilter}
                      onChange={(e) => setCategoryFilter(e.target.value)}
                    >
                      <option value="all">All categories</option>
                      {[
                        "business_regression",
                        "traffic_anomaly",
                        "security_signal",
                        "operational_incident",
                        "data_quality",
                        "inconclusive",
                      ].map((c) => (
                        <option key={c} value={c}>
                          {c.replaceAll("_", " ")}
                        </option>
                      ))}
                    </select>
                    <select
                      aria-label="Incident status"
                      value={statusFilter}
                      onChange={(e) => setStatusFilter(e.target.value)}
                    >
                      <option value="all">All statuses</option>
                      <option value="active">Open</option>
                      <option value="resolved">Resolved</option>
                      <option value="ignored">Ignored</option>
                      <option value="not_issue">Not an issue</option>
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
                  {github?.findings
                    ?.filter(
                      (x) =>
                        (categoryFilter === "all" ||
                          x.classification === categoryFilter) &&
                        (statusFilter === "all" || x.status === statusFilter) &&
                        x.summary.toLowerCase().includes(query.toLowerCase()),
                    )
                    .map((x) => (
                      <section
                        className="panel integration-settings"
                        key={x.id}
                      >
                        <h2>
                          {x.source === "shopify" ? "Shopify" : "GA4"} metric
                          change
                        </h2>
                        <span
                          className={
                            "badge " +
                            (x.classification === "business_regression" &&
                            x.status === "active"
                              ? "red"
                              : x.status === "resolved"
                                ? "green"
                                : "neutral")
                          }
                        >
                          {x.classification.replaceAll("_", " ")} ·{" "}
                          {x.status === "active"
                            ? "Open"
                            : reviewLabel(x.status)}
                        </span>
                        <p>{x.summary}</p>
                        <p className="muted">
                          {x.provider} · {x.mode} data
                        </p>
                        <p>{x.recommended_verification || x.limitation}</p>
                        {x.recommended_verification && x.limitation && (
                          <p className="muted">{x.limitation}</p>
                        )}
                        <div className="review-actions">
                          {[
                            ["resolve", "Mark resolved"],
                            ["ignore", "Ignore"],
                            ["not_issue", "Not an issue"],
                            ["reopen", "Reopen"],
                          ].map(([action, label]) => (
                            <button
                              key={action}
                              className="button secondary"
                              disabled={busy || publicAccess}
                              onClick={() =>
                                connectionRequest("integrations/review", {
                                  finding_id: x.id,
                                  action,
                                })
                              }
                            >
                              {label}
                            </button>
                          ))}
                        </div>
                      </section>
                    ))}
                  {data.history
                    .filter(
                      (x) =>
                        (categoryFilter === "all" ||
                          x.classification === categoryFilter) &&
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
                          setSelectedId(x.id);
                          setInvestigation(null);
                          setView("investigation");
                        }}
                      />
                    ))}
                  {data.history.length === 0 && !github?.findings?.length && (
                    <Empty
                      title="No incidents recorded"
                      description="Run a scenario to generate synthetic events and detect a regression."
                      action={() => setDemo(true)}
                    />
                  )}
                </>
              )}
              {view === "changes" && (
                <>
                  <PageHead
                    eyebrow="Release history"
                    title="Releases"
                    description="Review recorded releases and the components they changed."
                  />
                  <div className="panel table-panel">
                    <div className="table-scroll">
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
                    </div>
                    {!data.deployments.length && (
                      <Empty
                        title="No releases recorded"
                        description="Run a scenario to create a release record."
                        action={() => setDemo(true)}
                      />
                    )}
                  </div>
                  <div className="info-block">
                    <h2>Release correlation</h2>
                    <p>
                      Gemini compares eligible code changes with business
                      measurements. A candidate reference does not establish
                      causation.
                    </p>
                  </div>
                </>
              )}
              {view === "graph" && (
                <>
                  <PageHead
                    eyebrow="Dependency configuration"
                    title="Metric dependencies"
                    description="Configured relationships between components, customer activity, and business metrics."
                  />
                  <section className="panel graph-panel">
                    {[
                      {
                        name: "Checkout",
                        nodes: [
                          "checkout-service",
                          "Payment redirect",
                          "Checkout completion rate",
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
                          "Delivery time",
                          "Repeat purchase rate",
                          "Customer revenue",
                        ],
                      },
                    ].map((g, i) => (
                      <div className="graph-journey" key={g.name}>
                        <div className="eyebrow">
                          0{i + 1} / {g.name}
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
                                      "Component",
                                      "Customer activity",
                                      "Business metric",
                                      "Financial measure",
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
                    <h2>Dependency configuration</h2>
                    <p>
                      The graph defines which metrics to check after a component
                      changes. These relationships are configured explicitly.
                      Automatic dependency discovery is not implemented.
                    </p>
                  </div>
                </>
              )}
              {view === "banking" && (
                <>
                  <div className="page-head">
                    <div>
                      <div className="eyebrow">
                        Banking / settlement reconciliation
                      </div>
                      <h1>Unbacked credits</h1>
                      <p>
                        Compare application status, bank settlement status, and
                        ledger postings.
                      </p>
                    </div>
                    <button
                      className="button primary"
                      disabled={busy || (active && !publicAccess)}
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
                      <small>Existing reversal entries</small>
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
                        ? "Settlement status and ledger postings do not match."
                        : data.banking.total
                          ? "Reconciliation completed. Original postings and correction entries are retained."
                          : "No bank transactions available. Run the banking scenario."}
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
                        View incident <ArrowRight size={14} />
                      </button>
                    )}
                  </div>
                  <section className="panel integration-settings">
                    <h2>Accounts flagged for review</h2>
                    <p className="muted">
                      Gemini reviews repeated failed or pending transfers
                      recorded as successful credits. Flags are leads for
                      review, not fraud findings. No accounts are blocked.
                    </p>
                    {data.banking.account_reviews?.filter(
                      (r) => r.flag_for_review,
                    ).length ? (
                      data.banking.account_reviews
                        .filter((r) => r.flag_for_review)
                        .map((r) => {
                          const e = data.banking.accounts?.find(
                            (a) => a.account_id === r.account_id,
                          );
                          return (
                            <div className="account-review" key={r.account_id}>
                              <strong>{r.account_id}</strong>
                              <p>{r.reason}</p>
                              <p>
                                {e?.mismatch_count} mismatches ·{" "}
                                {money((e?.unbacked_cents || 0) / 100, 2)}{" "}
                                unbacked credits
                              </p>
                              <code>{r.transaction_ids.join(", ")}</code>
                            </div>
                          );
                        })
                    ) : (
                      <p>
                        No AI account flags are available. Run the banking
                        assessment to evaluate the evidence.
                      </p>
                    )}
                  </section>
                  <section className="panel table-panel">
                    <div className="panel-head">
                      <h2>Settlement evidence</h2>
                      <span className="muted">
                        Synthetic bank records · sample of affected transfers
                      </span>
                    </div>
                    <div className="table-scroll">
                      <table>
                        <thead>
                          <tr>
                            <th>Transaction</th>
                            <th>Bank status</th>
                            <th>Application status</th>
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
                    </div>
                    {!data.banking.total && (
                      <div className="no-changes">
                        Run the banking scenario to generate synthetic
                        transactions, settlement statuses, and ledger postings.
                      </div>
                    )}
                  </section>
                  <div className="info-block">
                    <h2>Reconciliation rules</h2>
                    <p>
                      A credit requires confirmed settlement. The detector
                      compares bank status with application status and the net
                      ledger balance. Review actions retain the original
                      postings and bank states. Production use requires verified
                      settlement data and approved accounting controls.
                    </p>
                  </div>
                </>
              )}
              {view === "commits" && (
                <>
                  <PageHead
                    eyebrow="Commit correlation"
                    title="Codebases"
                    description="Review candidate commits and their diffs."
                  />
                  <section className="panel github-connect">
                    <div>
                      <h2>Connect a codebase</h2>
                      <p>
                        {github?.connected
                          ? github.repo + " · read-only sync"
                          : "No repository is connected. The commits below are synthetic examples."}
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
                        disabled={busy || !repoInput || publicAccess}
                        onClick={async () => {
                          setBusy(true);
                          try {
                            setGithub(
                              await api("github/connect", { repo: repoInput }),
                            );
                            setToast("Commit import completed.");
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
                        Connect codebase
                      </button>
                    </div>
                  </section>
                  <section className="panel connection-repos">
                    <h2>Business metrics and instrumentation</h2>
                    <p className="muted">
                      Gemini assesses selected code excerpts and collected
                      connector fields. Recommendations are proposals; they do
                      not enable monitoring or change code.
                    </p>
                    <label htmlFor="business-context">Business context</label>
                    <textarea
                      id="business-context"
                      className="business-context"
                      maxLength={1200}
                      placeholder="Describe your business, successful outcomes, and accounting constraints."
                      value={businessContext}
                      onChange={(e) => setBusinessContext(e.target.value)}
                      disabled={publicAccess}
                    />
                    <div className="assessment-actions">
                      <button
                        className="button primary"
                        disabled={
                          busy ||
                          publicAccess ||
                          (!github?.repos?.length &&
                            !Object.keys(github?.snapshots || {}).length)
                        }
                        onClick={() => runMetricAssessment(false)}
                      >
                        Assess connected sources
                      </button>
                      <button
                        className="button"
                        disabled={busy}
                        onClick={() => runMetricAssessment(true)}
                      >
                        {publicAccess
                          ? "View example assessment"
                          : "Assess generated example"}
                      </button>
                    </div>
                    {metricAssessment && (
                      <>
                        <p className="muted">
                          {metricAssessment.provider}
                          {metricAssessment.cached
                            ? " · Cached assessment"
                            : ""}
                        </p>
                        <p>{metricAssessment.business_summary}</p>
                        {metricAssessment.metrics?.map((m, i) => (
                          <article className="metric-proposal" key={i}>
                            <div className="panel-head">
                              <h3>{m.name}</h3>
                              <span className="badge neutral">
                                {m.readiness.replaceAll("_", " ")}
                              </span>
                            </div>
                            <p>{m.business_question}</p>
                            <p>{m.definition}</p>
                            <p className="muted">
                              Required fields: {m.required_fields.join(", ")}
                            </p>
                            <p className="muted">{m.limitations}</p>
                            <p className="muted">
                              Evidence: {renderMetricRefs(m.evidence_refs)}
                            </p>
                            {m.sql_draft && (
                              <details>
                                <summary>Proposed SQL · not executed</summary>
                                <pre className="draft-diff">{m.sql_draft}</pre>
                              </details>
                            )}
                          </article>
                        ))}
                        {!!metricAssessment.logging?.length && (
                          <h3>Recommended logging</h3>
                        )}
                        {metricAssessment.logging?.map((l, i) => (
                          <article className="metric-proposal" key={i}>
                            <h3>
                              <code>{l.event_name}</code>
                            </h3>
                            <p>{l.purpose}</p>
                            <p>Emit: {l.when_to_emit}</p>
                            <p className="muted">
                              Fields: {l.fields.join(", ")}
                            </p>
                            <p className="muted">
                              Deduplication: {l.deduplication}
                            </p>
                            <p className="muted">
                              Evidence: {renderMetricRefs(l.evidence_refs)}
                            </p>
                          </article>
                        ))}
                        {!!metricAssessment.questions?.length && (
                          <>
                            <h3>Definitions to confirm</h3>
                            <ul>
                              {metricAssessment.questions.map((q, i) => (
                                <li key={i}>{q}</li>
                              ))}
                            </ul>
                          </>
                        )}
                        {metricAssessment.coverage?.map((c, i) => (
                          <p className="muted" key={i}>
                            {c.repo}: {c.coverage}
                            {c.eligible_files !== undefined
                              ? ` · ${c.files_scanned ?? "Selected"} of ${c.eligible_files} eligible files`
                              : ""}
                            {c.tree_truncated
                              ? " · Repository tree truncated"
                              : ""}
                          </p>
                        ))}
                        {metricAssessment.sources
                          ?.filter((s) => s.excerpt)
                          .map((s) => (
                            <details key={s.id}>
                              <summary>
                                {s.repo}/{s.file} · {s.revision.slice(0, 12)}
                              </summary>
                              <pre className="draft-diff">{s.excerpt}</pre>
                            </details>
                          ))}
                        <p className="muted">{metricAssessment.disclosure}</p>
                      </>
                    )}
                  </section>
                  <section className="panel connection-repos">
                    <h2>Project repositories</h2>
                    <p className="muted">
                      Attach multiple repositories to Luma Goods. Import is
                      read-only. Deployment mapping is required before
                      attributing an issue to an imported commit.
                    </p>
                    {github?.repos?.map((r) => (
                      <div className="connection-row" key={r.repo}>
                        <a
                          href={"https://github.com/" + r.repo}
                          target="_blank"
                          rel="noreferrer"
                        >
                          {r.repo}
                        </a>
                        <span>{r.commits.length} commits</span>
                        <button
                          className="text-button"
                          disabled={busy}
                          onClick={() =>
                            connectionRequest("github/remove", { repo: r.repo })
                          }
                        >
                          Disconnect
                        </button>
                      </div>
                    ))}
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
                      <div
                        className="commit-list-item"
                        key={c.repo + ":" + c.sha}
                      >
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
                              {c.repo} · {c.author} ·{" "}
                              {new Date(c.timestamp).toLocaleString("en-US", {
                                month: "short",
                                day: "numeric",
                                year: "numeric",
                                hour: "2-digit",
                                minute: "2-digit",
                              })}
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
                    <h2>Heuristic evaluation baseline</h2>
                    <p>
                      This optional comparison score uses commit time (30%),
                      service file overlap (30%), relevant diff terms (25%), and
                      affected segment terms (15%). Production attribution also
                      requires a verified deployment commit and the time the
                      metric changed.
                    </p>
                  </div>
                </>
              )}
              {view === "sources" && (
                <>
                  <PageHead
                    eyebrow="Event ingestion"
                    title="Integrations"
                    description="Collect commerce and analytics data, then inspect changes in business outcomes."
                  />
                  <section className="panel integration-settings">
                    <h2>Collection settings</h2>
                    <p className="muted">
                      Credentials stay in local environment variables. Samples
                      use generated data and do not access accounts.
                    </p>
                    <label>
                      Sample scenario
                      <select
                        value={sampleScenario}
                        onChange={(e) => setSampleScenario(e.target.value)}
                      >
                        <option value="checkout">
                          Checkout completion decrease
                        </option>
                        <option value="traffic">Traffic spike</option>
                        <option value="security">
                          Possible attack signals
                        </option>
                        <option value="data_quality">
                          Purchase event collection gap
                        </option>
                      </select>
                    </label>
                    <div className="integration-fields">
                      <label>
                        Shopify store
                        <input
                          placeholder="store.myshopify.com"
                          value={storeInput}
                          onChange={(e) => setStoreInput(e.target.value)}
                        />
                      </label>
                      <label>
                        GA4 property ID
                        <input
                          placeholder="123456789"
                          value={propertyInput}
                          onChange={(e) => setPropertyInput(e.target.value)}
                        />
                      </label>
                    </div>
                    <label>
                      AI analysis instructions
                      <textarea
                        maxLength={1500}
                        rows={3}
                        placeholder={github?.policy}
                        value={policyInput}
                        onChange={(e) => setPolicyInput(e.target.value)}
                      />
                    </label>
                    <button
                      className="button secondary"
                      disabled={busy || publicAccess}
                      onClick={() =>
                        connectionRequest("integrations/config", {
                          shopify_store: storeInput,
                          ga_property: propertyInput,
                          policy: policyInput || github?.policy,
                        })
                      }
                    >
                      Save settings
                    </button>
                    <p className="muted">
                      Vertex AI:{" "}
                      {publicAccess
                        ? "Cached demo analysis"
                        : github?.credentials?.vertex
                          ? "Configured"
                          : "Not configured"}
                      . Requests use compact aggregates, a 1,200-token output
                      limit, cached results, and a local request budget.
                    </p>
                  </section>
                  <div className="source-grid">
                    {[
                      [
                        "shopify",
                        "Shopify",
                        "Orders, payment states, amounts, and currencies. Customer and payment details are excluded.",
                      ],
                      [
                        "analytics",
                        "Google Analytics 4",
                        "Daily sessions, purchases, and purchase revenue. No user-level data is requested.",
                      ],
                    ].map(([id, title, description]) => {
                      const snapshot = github?.snapshots?.[id];
                      return (
                        <section className="panel source-card" key={id}>
                          <span
                            className={
                              "badge " + (snapshot ? "green" : "neutral")
                            }
                          >
                            {snapshot
                              ? snapshot.mode === "synthetic"
                                ? "Sample data"
                                : "Live collection"
                              : "Not collected"}
                          </span>
                          <h2>{title}</h2>
                          <p>{description}</p>
                          <div className="review-actions">
                            <button
                              className="button secondary"
                              disabled={busy}
                              onClick={() =>
                                connectionRequest("integrations/collect", {
                                  source: id,
                                  sample: true,
                                  scenario: sampleScenario,
                                })
                              }
                            >
                              Collect sample data
                            </button>
                            <button
                              className="button secondary"
                              disabled={busy || !github?.credentials?.[id]}
                              onClick={() =>
                                connectionRequest("integrations/collect", {
                                  source: id,
                                })
                              }
                            >
                              Collect from account
                            </button>
                            <button
                              className="text-button"
                              disabled={busy || !snapshot}
                              onClick={async () => {
                                setBusy(true);
                                try {
                                  setSourceAnalysis(
                                    await api("integrations/analyze", {
                                      source: id,
                                      scenario: sampleScenario,
                                    }),
                                  );
                                  setGithub(await api("github"));
                                } catch (e) {
                                  setError(e.message);
                                } finally {
                                  setBusy(false);
                                }
                              }}
                            >
                              Analyze metrics
                            </button>
                          </div>
                          {snapshot && (
                            <>
                              <p className="muted">
                                {snapshot.rows.length} records ·{" "}
                                {new Date(
                                  snapshot.collected_at,
                                ).toLocaleString()}
                              </p>
                              <div className="source-table">
                                <table>
                                  <thead>
                                    <tr>
                                      {Object.keys(snapshot.rows[0] || {}).map(
                                        (k) => (
                                          <th key={k}>
                                            {k.replaceAll("_", " ")}
                                          </th>
                                        ),
                                      )}
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {snapshot.rows.slice(-5).map((r, i) => (
                                      <tr key={i}>
                                        {Object.values(r).map((v, j) => (
                                          <td key={j}>{String(v)}</td>
                                        ))}
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </>
                          )}
                        </section>
                      );
                    })}
                  </div>
                  {sourceAnalysis && (
                    <section className="panel integration-settings">
                      <h2>Metric analysis</h2>
                      <span className="badge neutral">
                        {sourceAnalysis.classification.replaceAll("_", " ")}
                      </span>
                      <p>{sourceAnalysis.summary}</p>
                      <p>
                        {sourceAnalysis.recommended_verification ||
                          sourceAnalysis.limitation}
                      </p>
                      <p className="muted">
                        {sourceAnalysis.provider} · {sourceAnalysis.mode} data
                      </p>
                    </section>
                  )}
                  <section className="panel integration-settings">
                    <h2>Project tools</h2>
                    <div className="review-actions">
                      {[
                        ["changes", "Releases"],
                        ["banking", "Reconciliation"],
                        ["graph", "Metric dependencies"],
                        ["audit", "Audit log"],
                      ].map(([id, label]) => (
                        <button
                          className="text-button"
                          key={id}
                          onClick={() => setView(id)}
                        >
                          {label}
                        </button>
                      ))}
                    </div>
                  </section>
                  <section className="panel code-panel">
                    <div className="panel-head">
                      <h2>Event ingestion example</h2>
                      <button
                        className="text-button"
                        onClick={() => {
                          navigator.clipboard.writeText(example);
                          setToast("Example copied to the clipboard.");
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
                    eyebrow="Event history"
                    title="Audit log"
                    description="View recorded changes, detections, and operator actions."
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
            <div className="eyebrow">Synthetic data</div>
            <h2 id="demo-title">Run a demo scenario</h2>
            <p>
              Choose a scenario to generate synthetic events and investigate its
              business impact.
            </p>
            {scenarios.map((s) => (
              <button
                className="scenario-option"
                disabled={busy || (active && !publicAccess)}
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
                  "Scenario data reset to baseline.",
                );
                if (d) {
                  setDemo(false);
                  setView("overview");
                  setInvestigation(null);
                }
              }}
            >
              <RotateCcw size={15} />
              Reset demo data
            </button>
            <small className="modal-disclosure">
              Scenarios use synthetic data. They do not modify external systems.
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
          "incident-icon " +
          (["resolved", "recovered"].includes(f.status) ? "green-icon" : "")
        }
      >
        {["resolved", "recovered"].includes(f.status) ? (
          <CheckCircle2 size={23} />
        ) : (
          <TriangleAlert size={23} />
        )}
      </span>
      <div className="incident-main">
        <div className="incident-title">
          <span
            className={
              "badge " +
              (["resolved", "recovered"].includes(f.status)
                ? "green"
                : "orange")
            }
          >
            {["resolved", "recovered"].includes(f.status)
              ? "Resolved"
              : f.severity}
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
            : f.scenario === "promotion"
              ? "Estimated margin loss"
              : "Estimated revenue exposure"}
        </span>
      </div>
      <span className="investigate-link">
        View incident <ArrowUpRight size={16} />
      </span>
    </button>
  );
}
function numberedDiff(patch) {
  let current = null;
  return patch.split("\n").map((text) => {
    const h = text.match(/^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
    if (h) {
      current = Number(h[1]);
      return { text, newLine: null };
    }
    if (
      current === null ||
      text.startsWith("-") ||
      text.startsWith("\\") ||
      !["+", " "].includes(text[0])
    )
      return { text, newLine: null };
    return { text, newLine: current++ };
  });
}
function Diff({ commit, highlight }) {
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
            {numberedDiff(file.patch).map(({ text: line, newLine }, i) => (
              <span
                className={
                  (highlight?.suspect_commit_sha === commit.sha &&
                  highlight.file === file.filename &&
                  highlight.line === newLine
                    ? "ai-line "
                    : "") +
                  (line.startsWith("+")
                    ? "added"
                    : line.startsWith("-")
                      ? "removed"
                      : "context")
                }
                key={i}
              >
                <>
                  <span className="line-number">{newLine ?? ""}</span>
                  {line + "\n"}
                </>
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
