import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor: Dynamically inject JWT token on outbound REST queries
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('uabe_access_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response Interceptor: Catch 401 token expiry exceptions and wipe credentials if session invalid
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // Check if error is 401 Unauthorized and request has not been retried
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem('uabe_refresh_token');
      
      if (refreshToken) {
        try {
          // Attempt to refresh the JWT session token
          const res = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });
          
          const newAccessToken = res.data.access_token;
          localStorage.setItem('uabe_access_token', newAccessToken);
          
          // Re-attempt original request with updated authorization token
          originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
          return api(originalRequest);
        } catch (refreshError) {
          // Refresh failed - wipe credentials
          localStorage.removeItem('uabe_access_token');
          localStorage.removeItem('uabe_refresh_token');
          window.dispatchEvent(new Event('auth_logout'));
        }
      } else {
        localStorage.removeItem('uabe_access_token');
        window.dispatchEvent(new Event('auth_logout'));
      }
    }
    
    return Promise.reject(error);
  }
);
