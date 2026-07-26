import axios from "axios";

const API_URL = "http://127.0.0.1:8000";


export async function getMT5Account() {
  const response = await axios.get(
    `${API_URL}/mt5/account`
  );

  return response.data;
}


export async function getMT5Positions() {
  const response = await axios.get(
    `${API_URL}/mt5/positions`
  );

  return response.data;
}