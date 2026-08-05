import axios from "axios";

const API_URL =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.DEV
    ? `http://${window.location.hostname}:8000`
    : "https://bethel-api.onrender.com");
const TOKEN_KEY = "bethel_subscriber_access_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function saveSession(data) {
  localStorage.setItem(TOKEN_KEY, data.access_token);
  localStorage.setItem("bethel_subscriber_id", String(data.subscriber_id));
  localStorage.setItem("bethel_subscriber_name", data.name || "Investor");
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem("bethel_subscriber_id");
  localStorage.removeItem("bethel_subscriber_name");
}

export function getSubscriberId() {
  return Number(localStorage.getItem("bethel_subscriber_id")) || null;
}

export function isAuthenticated() {
  return Boolean(getToken() && getSubscriberId());
}

export async function registerSubscriber(email, password) {
  const response = await axios.post(
    `${API_URL}/copytrading/auth/register`,
    { email, password }
  );
  return response.data;
}

export async function loginSubscriber(email, password) {
  const response = await axios.post(
    `${API_URL}/copytrading/auth/login`,
    { email, password }
  );
  saveSession(response.data);
  return response.data;
}
