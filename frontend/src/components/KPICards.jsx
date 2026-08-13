import { ChartNoAxesCombined } from 'lucide-react'

const labelFor = (key) => key
  .replaceAll('_', ' ')
  .replace(/\b\w/g, (letter) => letter.toUpperCase())

const labels = {
  record_count: 'Record Count',
  employee_count: 'Employee Count',
  attrition_rate: 'Attrition Rate',
}

const formatNumber = (value, key) => {
  if (value == null) return 'Not available'
  const suffix = key.includes('margin') || key.includes('percent') || key.includes('percentage') ? '%' : ''
  return `${new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(value)}${suffix}`
}

export default function KPICards({ metrics }) {
  const cards = Object.entries(metrics || {}).filter(([, value]) => value != null)
  if (!cards.length) return null
  return <section><div className="section-heading"><span className="eyebrow">Key metrics</span><h2>Performance summary</h2></div><div className="kpi-grid">{cards.map(([key, value]) => <article className="kpi-card" key={key}><ChartNoAxesCombined size={20} /><span>{labels[key] || labelFor(key)}</span><strong>{formatNumber(value, key)}</strong></article>)}</div></section>
}
