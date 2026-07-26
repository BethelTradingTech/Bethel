import axios from "axios";
import { clearSession, getToken } from "./auth";

export const API_URL =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.DEV
    ? `http://${window.location.hostname}:8000`
    : "https://api.betheltradingtechnologies.com");

export const api = axios.create({
  baseURL: API_URL,
  headers: { Accept: "application/json" }
});

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearSession();
    }
    return Promise.reject(error);
  }
);

export async function getPlans() {
  return (await api.get("/onboarding/plans")).data;
}

export async function selectPlan(subscriberId, planId) {
  return (
    await api.post(`/onboarding/${subscriberId}/subscription`, {
      plan_id: planId
    })
  ).data;
}

export async function connectMT5(subscriberId, data) {
  return (
    await api.post(
      `/copytrading/onboarding/connect-mt5/${subscriberId}`,
      data
    )
  ).data;
}

export async function getOnboardingStatus(subscriberId) {
  return (await api.get(`/onboarding/${subscriberId}`)).data;
}

export async function getSubscriberPerformance(subscriberId) {
  return (
    await api.get(`/copytrading/subscribers/${subscriberId}/performance`)
  ).data;
}

export async function getOrders() {
  return (await api.get("/copytrading/orders")).data;
}

export async function getEquityHistory() {
  return (await api.get("/performance/equity-history")).data;
}

export async function getAnalytics() {
  return (await api.get("/performance/analytics")).data;
}

export async function getSubscribers() {
  return (await api.get("/copytrading/subscribers")).data;
}

export async function getCopyOrders() {
  return (await api.get("/copytrading/orders")).data;
}

export async function getMT5Account() {
  return (await api.get("/mt5/account")).data;
}

export async function getMT5Positions() {
  return (await api.get("/mt5/positions")).data;
}
