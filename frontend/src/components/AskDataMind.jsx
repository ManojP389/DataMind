import { useState } from 'react'
import { LoaderCircle, Send } from 'lucide-react'
import ExecutionTrace from './ExecutionTrace'
import { getApiErrorMessage, queryDataset } from '../services/api'
import './AskDataMind.css'

const examples = [
  'Which region has the highest profit?',
  'Which category has the highest sales?',
  'Which segment has the highest profit?',
]

const sqlAgents = new Set(['manager', 'data_agent', 'eda_agent', 'sql_agent'])

export default function AskDataMind({ fileId }) {
  const [question, setQuestion] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function askQuestion(event) {
    event.preventDefault()
    const userRequest = question.trim()
    if (!userRequest || !fileId) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      setResult(await queryDataset(fileId, userRequest))
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    } finally {
      setLoading(false)
    }
  }

  const sqlResult = result?.sql_result
  const insight = typeof result?.insight === 'string' ? result.insight.trim() : ''

  return <section className="ask-data-card" aria-labelledby="ask-title">
    <div className="section-heading"><span className="eyebrow">Natural-language query</span><h2 id="ask-title">Ask DataMind</h2><p>Ask a question about the uploaded dataset and DataMind will query it for you.</p></div>
    <form className="ask-form" onSubmit={askQuestion}>
      <textarea value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="For example: Which region has the highest profit?" rows="3" disabled={loading} />
      <button type="submit" disabled={!question.trim() || loading}>{loading ? <LoaderCircle className="spin" size={18} /> : <Send size={18} />}{loading ? 'Asking…' : 'Ask'}</button>
    </form>
    <div className="example-questions">{examples.map((example) => <button className="example-question" type="button" key={example} onClick={() => setQuestion(example)} disabled={loading}>{example}</button>)}</div>
    {error && <p className="error-message" role="alert">{error}</p>}
    {sqlResult && <div className="query-result" aria-live="polite">
      <div className="query-question"><span>Question</span><p>{sqlResult.question}</p></div>
      <section className="ai-insight" aria-labelledby="ai-insight-title"><span className="eyebrow">AI analysis</span><h3 id="ai-insight-title">AI Insight</h3><p>{insight || 'No insight available.'}</p></section>
      <section className="query-section" aria-labelledby="sql-query-title"><h3 id="sql-query-title">SQL Query</h3><code>{sqlResult.sql}</code></section>
      <section className="query-section" aria-labelledby="query-results-title"><h3 id="query-results-title">Query Results</h3>{sqlResult.rows?.length ? <div className="result-table-wrap"><table><thead><tr>{sqlResult.columns.map((column) => <th key={column}>{column}</th>)}</tr></thead><tbody>{sqlResult.rows.map((row, index) => <tr key={index}>{sqlResult.columns.map((column) => <td key={column}>{row[column] == null ? '—' : String(row[column])}</td>)}</tr>)}</tbody></table></div> : <p className="no-results">The query returned no rows.</p>}</section>
      <ExecutionTrace execution={result.execution?.filter(({ agent }) => sqlAgents.has(agent))} eyebrow="SQL Agent execution" title="Query workflow" />
    </div>}
  </section>
}
