// frontend/src/api/index.js
const BASE = '/api'

async function request(method, path, { body, params } = {}) {
  let url = BASE + path
  if (params) {
    const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v != null))
    if (qs.toString()) url += '?' + qs
  }
  const resp = await fetch(url, {
    method,
    body,
    // Don't set Content-Type for FormData (browser sets it with boundary)
    ...(body instanceof FormData ? {} : { headers: { 'Content-Type': 'application/json' } }),
  })
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }))
    throw new Error(err.detail || resp.statusText)
  }
  if (resp.status === 204) return null
  return resp.json()
}

export const api = {
  // Accounts
  listAccounts: () => request('GET', '/accounts'),
  getCredit: (id) => request('GET', `/accounts/${id}/credit`),

  // Tasks
  submitTask: (formData) => request('POST', '/tasks', { body: formData }),
  listTasks: (filters = {}) => request('GET', '/tasks', { params: filters }),
  getTask: (id) => request('GET', `/tasks/${id}`),
  deleteTask: (id) => request('DELETE', `/tasks/${id}`),
  copyTask: (id) => request('POST', `/tasks/${id}/copy`),

  // Projects
  listProjects: (includeDeleted = false) => request('GET', '/projects', { params: { include_deleted: includeDeleted } }),
  createProject: (name) => request('POST', '/projects', { body: JSON.stringify({ name }) }),
  getProject: (id) => request('GET', `/projects/${id}`),
  updateProject: (id, name) => request('PUT', `/projects/${id}`, { body: JSON.stringify({ name }) }),
  deleteProject: (id, permanent = false) => request('DELETE', `/projects/${id}`, { params: { permanent } }),
  restoreProject: (id) => request('POST', `/projects/${id}/restore`),
  getProjectStats: (id) => request('GET', `/projects/${id}/stats`),

  // Materials
  listMaterials: (projectId, type = null) => request('GET', `/projects/${projectId}/materials`, { params: { type } }),
  createMaterial: (projectId, formData) => request('POST', `/projects/${projectId}/materials`, { body: formData }),
  updateMaterial: (projectId, materialId, name) => request('PUT', `/projects/${projectId}/materials/${materialId}`, { body: JSON.stringify({ name }) }),
  deleteMaterial: (projectId, materialId) => request('DELETE', `/projects/${projectId}/materials/${materialId}`),
}