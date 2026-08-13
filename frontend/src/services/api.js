import axios from 'axios'

// The Vite development proxy forwards /api to VITE_API_BASE_URL. Keeping the
// browser request same-origin avoids requiring any FastAPI/CORS changes.
const apiBaseUrl = import.meta.env.DEV
  ? '/api'
  : (import.meta.env.VITE_API_BASE_URL || '/api')
const client = axios.create({ baseURL: apiBaseUrl.replace(/\/$/, '') })

function messageFromResponse(response) {
  const detail = response?.data?.detail
  if (Array.isArray(detail)) return detail.map((item) => item.msg).filter(Boolean).join(' ')
  return typeof detail === 'string' ? detail : null
}

export function getApiErrorMessage(error) {
  return messageFromResponse(error.response)
    || (error.request ? 'Cannot reach the DataMind backend. Check that it is running and try again.' : null)
    || error.message
    || 'The dataset could not be analyzed. Please try again.'
}

export async function uploadAndAnalyze(file) {
  const formData = new FormData()
  formData.append('file', file)
  const upload = await client.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  if (!upload.data?.file_id) throw new Error('The upload completed but did not return a dataset ID.')
  const analysis = await client.post(`/agent/analyze/${upload.data.file_id}`)
  return { fileId: upload.data.file_id, ...analysis.data }
}

export async function queryDataset(fileId, userRequest) {
  const response = await client.post(`/agent/query/${fileId}`, null, {
    params: { user_request: userRequest },
  })
  return response.data
}
