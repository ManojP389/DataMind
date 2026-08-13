import { FileUp, LoaderCircle, Upload } from 'lucide-react'

export default function FileUpload({ file, loading, error, onFileChange, onSubmit }) {
  return (
    <section className="upload-card" aria-labelledby="upload-title">
      <div>
        <span className="eyebrow">Start an analysis</span>
        <h2 id="upload-title">Upload a CSV dataset</h2>
        <p>DataMind profiles the data, finds patterns, and returns interactive chart specifications.</p>
      </div>
      <form onSubmit={onSubmit} className="upload-controls">
        <label className="file-picker">
          <FileUp size={19} aria-hidden="true" />
          <span>{file?.name || 'Choose a CSV file'}</span>
          <input type="file" accept=".csv,text/csv" onChange={onFileChange} />
        </label>
        <button type="submit" disabled={!file || loading}>
          {loading ? <LoaderCircle className="spin" size={18} /> : <Upload size={18} />}
          {loading ? 'Analyzing…' : 'Upload & analyze'}
        </button>
      </form>
      {error && <p className="error-message" role="alert">{error}</p>}
    </section>
  )
}
