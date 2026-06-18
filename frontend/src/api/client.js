import axios from "axios";

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "",
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

client.interceptors.request.use((config) => {
  const persisted = localStorage.getItem("scf_auth");
  const token = persisted ? JSON.parse(persisted)?.state?.token : null;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("scf_auth");
      if (window.location.pathname !== "/login") window.location.assign("/login");
    }
    return Promise.reject(error);
  },
);

export const apiErrorMessage = (error) =>
  error.response?.data?.message || error.response?.data?.error || error.message || "Something went wrong";

export default client;
