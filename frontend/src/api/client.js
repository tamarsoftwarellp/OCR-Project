import axios from "axios";

const STORAGE_KEY = "claim_ocr_api_base_url";
const DEFAULT_BASE_URL = "http://localhost:8000";
const ACCESS_TOKEN_KEY = "claim_ocr_access_token";
const REFRESH_TOKEN_KEY = "claim_ocr_refresh_token";

export function getBaseUrl() {
  return localStorage.getItem(STORAGE_KEY) || DEFAULT_BASE_URL;
}

export function setBaseUrl(url) {
  localStorage.setItem(STORAGE_KEY, url.replace(/\/+$/, ""));
}

// ---- Token storage ----
export function getAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setTokens({ access_token, refresh_token }) {
  if (access_token) localStorage.setItem(ACCESS_TOKEN_KEY, access_token);
  if (refresh_token) localStorage.setItem(REFRESH_TOKEN_KEY, refresh_token);
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

// Called from AuthContext so client.js can redirect to /login on hard
// auth failure (refresh token expired/invalid) without importing React
// Router here.
let onAuthExpired = () => {};
export function setOnAuthExpired(handler) {
  onAuthExpired = handler;
}

// Only these are called *before* we have a session (or to establish one),
// so they should never carry a stale Bearer token, and a 401 from them is
// a real auth failure, not an "access token expired, please refresh" case.
// /auth/me is deliberately NOT in this list - it's a protected endpoint
// and needs the same token-attach + refresh-on-401 behavior as everything
// else, or every login would 401 on the very next /auth/me call.
const PUBLIC_AUTH_PATHS = ["/auth/signup", "/auth/login", "/auth/refresh"];

function isPublicAuthEndpoint(url) {
  return PUBLIC_AUTH_PATHS.some((path) => url?.startsWith(path));
}

export const api = axios.create({
  baseURL: getBaseUrl(),
});

api.interceptors.request.use((config) => {
  config.baseURL = getBaseUrl();
  const token = getAccessToken();
  if (token && !isPublicAuthEndpoint(config.url)) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Refresh-on-401: queue concurrent requests behind a single in-flight
// refresh call instead of firing one refresh per failed request.
let refreshPromise = null;

async function performRefresh() {
  const refresh_token = getRefreshToken();
  if (!refresh_token) throw new Error("No refresh token");
  const res = await axios.post(`${getBaseUrl()}/auth/refresh`, {
    refresh_token,
  });
  setTokens(res.data);
  return res.data.access_token;
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { config, response } = error;
    const isPublicAuth = isPublicAuthEndpoint(config?.url);

    if (response?.status === 401 && !isPublicAuth && !config._retried) {
      config._retried = true;
      try {
        refreshPromise = refreshPromise || performRefresh();
        const newAccessToken = await refreshPromise;
        refreshPromise = null;
        config.headers.Authorization = `Bearer ${newAccessToken}`;
        return api(config);
      } catch (refreshErr) {
        refreshPromise = null;
        clearTokens();
        onAuthExpired();
        return Promise.reject(refreshErr);
      }
    }
    return Promise.reject(error);
  }
);

// ---- Auth ----
export const signup = (email, password, name) =>
  api.post("/auth/signup", { email, password, name });

export const login = (email, password) =>
  api.post("/auth/login", { email, password });

export const refreshTokens = () => performRefresh();

export const getMe = () => api.get("/auth/me");

// ---- Claims ----
export const uploadClaim = (file, fileNo, onProgress) => {
  const form = new FormData();
  form.append("file", file);
  if (fileNo) form.append("file_no", fileNo);
  return api.post("/claims/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (evt) => {
      if (onProgress && evt.total) {
        onProgress(Math.round((evt.loaded * 100) / evt.total));
      }
    },
  });
};

export const listClaims = (params) => api.get("/claims", { params });

export const getClaim = (claimId) => api.get(`/claims/${claimId}`);

export const deleteClaim = (claimId) => api.delete(`/claims/${claimId}`);

export const updateClaimStatus = (claimId, status) =>
  api.patch(`/claims/${claimId}/status`, { status });

// ---- Documents ----
export const listDocuments = (claimId) =>
  api.get(`/claims/${claimId}/documents`);

export const getDocument = (claimId, documentType) =>
  api.get(`/claims/${claimId}/documents/${documentType}`);

// Backend expects one field at a time: { key: "field_name", value: "new value" }
export const updateEntity = (claimId, documentType, key, value) =>
  api.patch(`/claims/${claimId}/documents/${documentType}/entities`, {
    key,
    value,
  });

// Convenience: save several changed fields by firing one PATCH per field.
export const updateEntities = async (claimId, documentType, changedFields) => {
  const entries = Object.entries(changedFields);
  const results = [];
  for (const [key, value] of entries) {
    results.push(await updateEntity(claimId, documentType, key, value));
  }
  return results;
};

// Reviewer removes a field entirely (not just blanks it out).
export const deleteEntity = (claimId, documentType, key) =>
  api.delete(
    `/claims/${claimId}/documents/${documentType}/entities/${encodeURIComponent(key)}`
  );

// Reviewer adds/edits/removes tables, rows, columns, or cells - sends the
// whole edited tables array in one shot (tables are dynamic in shape).
export const updateTables = (claimId, documentType, tables) =>
  api.put(`/claims/${claimId}/documents/${documentType}/tables`, { tables });

export const checkHealth = () => api.get("/health");