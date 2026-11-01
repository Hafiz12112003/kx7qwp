import { useEffect, useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";

const API = import.meta.env.VITE_API_URL || "";
const fmt = (n) => (n == null ? "-" : Math.round(n).toLocaleString());

async function getJson(path) {
  const res = await fetch(API + path);
  if (!res.ok) throw new Error("Request failed: " + path);
  return res.json();
}

function Card({ label, value, note }) {
  return (
    <div className="card">
      <div className="l">{label}</div>
      <div className="v">{value}</div>
      {note && <div className="n">{note}</div>}
    </div>
  );
}

export default function App() {
  const [cutoff, setCutoff] = useState(9);
  const [date, setDate] = useState("2026-01-12");
  const [acc, setAcc] = useState(null);
  const [day, setDay] = useState(null);
  const [horizon, setHorizon] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    getJson("/api/horizon").then(setHorizon).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    getJson("/api/accuracy?cutoff_hour=" + cutoff)
      .then(setAcc)
      .catch((e) => setError(e.message));
  }, [cutoff]);

  useEffect(() => {
    getJson("/api/day?date=" + date + "&cutoff_hour=" + cutoff)
      .then(setDay)
      .catch((e) => setError(e.message));
  }, [date, cutoff]);

  const s = acc ? acc.summary : null;
  const margin = s ? s.err_p90 : 0;

  const dayData = day
    ? day.points.map((p) => ({
        t: p.time.slice(11, 16),
        Forecast: p.forecast,
        Actual: p.actual,
        "Conservative (forecast - P90 error)": Math.max(0, p.forecast - margin),
      }))
    : [];

  return (
    <div className="wrap">
      <h1>UK Wind Generation: Forecast Monitor</h1>
      <p className="sub">
        Day-ahead buying support, January 2026. Source: Elexon BMRS (WINDFOR forecasts, FUELHH actuals).
      </p>

      {error && <div className="err">{error}</div>}

      <div className="controls">
        <label>
          Delivery day
          <input
            type="date"
            value={date}
            min="2026-01-01"
            max="2026-01-31"
            onChange={(e) => e.target.value && setDate(e.target.value)}
          />
        </label>
        <label>
          Decision cutoff (D-1, UK time)
          <select value={cutoff} onChange={(e) => setCutoff(Number(e.target.value))}>
            {[6, 8, 9, 10, 11, 12].map((h) => (
              <option key={h} value={h}>
                {String(h).padStart(2, "0")}:00
              </option>
            ))}
          </select>
        </label>
      </div>

      {s && (
        <div className="cards">
          <Card label="Mean abs error (MAE)" value={fmt(s.mae) + " MW"} note={s.mae_pct + "% of mean actual"} />
          <Card label="Bias (forecast - actual)" value={fmt(s.bias) + " MW"} note="positive = over-forecast" />
          <Card label="RMSE" value={fmt(s.rmse) + " MW"} />
          <Card label="MAPE" value={s.mape + "%"} />
          <Card label="90th pct over-forecast" value={fmt(s.err_p90) + " MW"} note="used as safety margin" />
        </div>
      )}

      <div className="panel">
        <h2>Forecast available at decision time vs actual: {date}</h2>
        <p>
          Latest forecast published before the cutoff
          {day ? " (" + day.cutoff.replace("T", " ").replace(":00Z", " UTC") + ")" : ""}. The conservative line
          subtracts the month's 90th-percentile over-forecast, based on in-sample January errors.
        </p>
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={dayData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="t" interval={3} />
            <YAxis tickFormatter={(v) => v / 1000 + " GW"} />
            <Tooltip formatter={(v) => fmt(v) + " MW"} />
            <Legend />
            <Line type="monotone" dataKey="Forecast" stroke="#1f77b4" dot={false} strokeWidth={2} />
            <Line type="monotone" dataKey="Actual" stroke="#2ca02c" dot={false} strokeWidth={2} />
            <Line
              type="monotone"
              dataKey="Conservative (forecast - P90 error)"
              stroke="#d62728"
              strokeDasharray="5 4"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
        {day && day.summary && (
          <p style={{ marginTop: 8 }}>
            This day: MAE {fmt(day.summary.mae)} MW, bias {fmt(day.summary.bias)} MW.
          </p>
        )}
      </div>

      <div className="panel">
        <h2>Daily bias across January</h2>
        <p>Click a bar to load that day above.</p>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart
            data={acc ? acc.daily : []}
            onClick={(e) => e && e.activeLabel && setDate(e.activeLabel)}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tickFormatter={(d) => d.slice(8)} />
            <YAxis />
            <Tooltip formatter={(v) => fmt(v) + " MW"} />
            <Legend />
            <Bar dataKey="bias" name="Bias (MW)" fill="#ff7f0e" />
            <Bar dataKey="mae" name="MAE (MW)" fill="#1f77b4" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="panel">
        <h2>Error by forecast horizon</h2>
        <p>Hours between publish time and target time, all forecasts for January targets.</p>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={horizon}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="horizon" />
            <YAxis />
            <Tooltip formatter={(v) => fmt(v) + " MW"} />
            <Legend />
            <Bar dataKey="mae" name="MAE (MW)" fill="#1f77b4" />
            <Bar dataKey="bias" name="Bias (MW)" fill="#ff7f0e" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
