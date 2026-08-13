import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from 'recharts'

const colors = ['#38bdf8', '#818cf8', '#34d399', '#fbbf24', '#fb7185', '#a78bfa']

function Chart({ chart }) {
  const common = <><CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" /><XAxis dataKey={chart.x_axis} interval={0} angle={chart.data.length > 6 ? -25 : 0} textAnchor={chart.data.length > 6 ? 'end' : 'middle'} height={chart.data.length > 6 ? 65 : 30} /><YAxis /><Tooltip /><Legend /></>
  if (chart.chart_type === 'line') return <LineChart data={chart.data}>{common}<Line type="monotone" dataKey={chart.y_axis} stroke="#4f46e5" strokeWidth={3} dot={{ r: 3 }} /></LineChart>
  if (chart.chart_type === 'scatter') return <ScatterChart>{common}<Scatter name={chart.title} data={chart.data} fill="#0ea5e9" /></ScatterChart>
  if (chart.chart_type === 'pie') return <PieChart><Tooltip /><Legend /><Pie data={chart.data} dataKey={chart.y_axis} nameKey={chart.x_axis} cx="50%" cy="50%" outerRadius={92} label>{chart.data.map((_, index) => <Cell key={index} fill={colors[index % colors.length]} />)}</Pie></PieChart>
  return <BarChart data={chart.data}>{common}<Bar dataKey={chart.y_axis} fill="#4f46e5" radius={[5, 5, 0, 0]} /></BarChart>
}

export default function ChartRenderer({ charts }) {
  if (!charts?.length) return <section className="notice"><span className="eyebrow">Visualizations</span><h2>No charts available</h2><p>This dataset did not contain a grouping and metric suitable for a chart.</p></section>
  return <section><div className="section-heading"><span className="eyebrow">Visualizations</span><h2>Explore the results</h2></div><div className="chart-grid">{charts.map((chart, index) => <article className="chart-card" key={`${chart.title}-${index}`}><h3>{chart.title}</h3><div className="chart"><ResponsiveContainer width="100%" height="100%"><Chart chart={chart} /></ResponsiveContainer></div></article>)}</div></section>
}
