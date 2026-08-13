import { useState } from 'react'
import { BarChart3 } from 'lucide-react'
import Header from './components/Header'
import FileUpload from './components/FileUpload'
import DatasetOverview from './components/DatasetOverview'
import KPICards from './components/KPICards'
import ChartRenderer from './components/ChartRenderer'
import Insights from './components/Insights'
import ExecutionTrace from './components/ExecutionTrace'
import AskDataMind from './components/AskDataMind'
import { getApiErrorMessage, uploadAndAnalyze } from './services/api'

export default function App() {
  const [file, setFile] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
    if (!file) return
    setLoading(true)
    setError('')
    setAnalysis(null)
    try {
      setAnalysis(await uploadAndAnalyze(file))
    } catch (requestError) {
      setError(getApiErrorMessage(requestError))
    } finally {
      setLoading(false)
    }
  }

  return <><Header /><main><FileUpload file={file} loading={loading} error={error} onFileChange={(event) => { setFile(event.target.files?.[0] || null); setError('') }} onSubmit={handleSubmit} />{loading ? <section className="empty-state" aria-live="polite"><BarChart3 className="spin" size={42} /><h2>Analyzing your dataset</h2><p>DataMind is profiling your data, running exploratory analysis, and preparing visualizations.</p></section> : analysis ? <div className="dashboard"><DatasetOverview profile={analysis.dataset_profile} /><KPICards metrics={analysis.eda_results?.overall_metrics} /><ChartRenderer charts={analysis.visualization_results} /><Insights insights={analysis.eda_results?.business_insights} /><ExecutionTrace execution={analysis.execution} /><AskDataMind fileId={analysis.fileId} /></div> : <section className="empty-state"><BarChart3 size={42} /><h2>Your analytics workspace is ready</h2><p>Upload a CSV to view dataset metrics, insights, agent execution, and interactive charts.</p></section>}</main></>
}
