import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const refresh = localStorage.getItem('refresh_token')
      if (refresh) {
        try {
          const { data } = await axios.post('/api/auth/refresh', { refresh_token: refresh })
          localStorage.setItem('access_token', data.access_token)
          localStorage.setItem('refresh_token', data.refresh_token)
          original.headers.Authorization = `Bearer ${data.access_token}`
          return api(original)
        } catch {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(error)
  }
)

export default api

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authApi = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  verifyEmail: (data) => api.post('/auth/verify-email', data),
  resendVerification: (data) => api.post('/auth/resend-verification', data),
  forgotPassword: (data) => api.post('/auth/forgot-password', data),
  resetPassword: (data) => api.post('/auth/reset-password', data),
  refresh: (data) => api.post('/auth/refresh', data),
  logout: (data) => api.post('/auth/logout', data),
  me: () => api.get('/auth/me'),
  updateMe: (data) => api.patch('/auth/me', data),
  changePassword: (data) => api.patch('/auth/me/password', data),
}

// ── Listings ──────────────────────────────────────────────────────────────────
export const listingsApi = {
  list: (params) => api.get('/listings', { params }),
  get: (id) => api.get(`/listings/${id}`),
  create: (data) => api.post('/listings', data),
  update: (id, data) => api.patch(`/listings/${id}`, data),
  delete: (id) => api.delete(`/listings/${id}`),
  myListings: (params) => api.get('/listings/vendor/my-listings', { params }),
  allergenCheck: (data) => api.post('/listings/allergen-check', data),
}

// ── Orders ────────────────────────────────────────────────────────────────────
export const ordersApi = {
  create: (data) => api.post('/orders', data),
  list: (params) => api.get('/orders', { params }),
  get: (id) => api.get(`/orders/${id}`),
  updateStatus: (id, data) => api.patch(`/orders/${id}/status`, data),
}

// ── Payments ──────────────────────────────────────────────────────────────────
export const paymentsApi = {
  initiate: (orderId) => api.post(`/payments/${orderId}/initiate`),
  simulateSuccess: (orderId) => api.post(`/payments/${orderId}/simulate-success`),
  status: (orderId) => api.get(`/payments/${orderId}/status`),
}

// ── Vendors ───────────────────────────────────────────────────────────────────
export const vendorsApi = {
  register: (data) => api.post('/vendors/register', data),
  me: () => api.get('/vendors/me'),
  get: (id) => api.get(`/vendors/${id}`),
}

// ── Admin ─────────────────────────────────────────────────────────────────────
export const adminApi = {
  stats: () => api.get('/admin/stats'),
  users: (params) => api.get('/admin/users', { params }),
  getUser: (id) => api.get(`/admin/users/${id}`),
  updateUser: (id, data) => api.patch(`/admin/users/${id}`, data),
  deleteUser: (id) => api.delete(`/admin/users/${id}`),
  vendors: (params) => api.get('/admin/vendors', { params }),
  approveVendor: (id, data) => api.patch(`/admin/vendors/${id}/approve`, data),
  deleteVendor: (id) => api.delete(`/admin/vendors/${id}`),
  listings: (params) => api.get('/admin/listings', { params }),
  updateListing: (id, data) => api.patch(`/admin/listings/${id}`, data),
  deleteListing: (id) => api.delete(`/admin/listings/${id}`),
  orders: (params) => api.get('/admin/orders', { params }),
  getOrder: (id) => api.get(`/admin/orders/${id}`),
  triggerDecay: () => api.post('/admin/trigger-price-decay'),
  jobs: () => api.get('/jobs/status'),
}
