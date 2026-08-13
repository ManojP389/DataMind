import { Columns3, Database, ListTree, Tags } from 'lucide-react'

const items = [
  ['row_count', 'Rows', Database],
  ['column_count', 'Columns', Columns3],
  ['numerical_columns', 'Numerical columns', ListTree],
  ['categorical_columns', 'Categorical columns', Tags],
]

export default function DatasetOverview({ profile }) {
  return (
    <section>
      <div className="section-heading"><span className="eyebrow">Dataset overview</span><h2>Data at a glance</h2></div>
      <div className="overview-grid">
        {items.map(([key, label, Icon]) => {
          const value = Array.isArray(profile[key]) ? profile[key].length : profile[key]
          return <article className="stat-card" key={key}><Icon size={20} /><span>{label}</span><strong>{value ?? 0}</strong></article>
        })}
      </div>
    </section>
  )
}
