import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

const api = axios.create({
  baseURL: API_BASE,
  timeout: 120000,
  headers: { 'Content-Type': 'application/json' },
})

// ─── Stock Prediction ───────────────────────────────────────────
export async function predictStock(ticker, period = '2y', market = 'auto') {
  const response = await api.post('/predict', { ticker, period, market })
  return response.data
}

// ─── Historical Data ────────────────────────────────────────────
export async function getStockHistory(ticker, period = '1y', market = 'auto') {
  const response = await api.get(`/history/${ticker}`, { params: { period, market } })
  return response.data
}

// ─── Trending Stocks ────────────────────────────────────────────
export async function getTrendingStocks() {
  const response = await api.get('/trending')
  return response.data
}

// ─── Health Check ───────────────────────────────────────────────
export async function healthCheck() {
  const response = await api.get('/health')
  return response.data
}

export default api

// Saved historical analytics. Pin follow-up requests to the overview's completed run.
export async function getAnalyticsOverview(signal) {
  return (await api.get('/analytics/overview', { signal })).data
}
export async function getAnalyticsRankings(params, signal) {
  return (await api.get('/analytics/rankings', { params, signal })).data
}
export async function getAnalyticsStock(ticker, params, signal) {
  return (await api.get(`/analytics/stock/${encodeURIComponent(ticker)}`, { params, signal })).data
}
export async function getAnalyticsBenchmarks(run, signal) {
  return (await api.get('/analytics/benchmarks', { params: { run }, signal })).data
}
