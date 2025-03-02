console.log("API Base URL:", process.env.VUE_APP_API_BASE_URL);
// src/services/api.js
import axios from "axios";

const apiClient = axios.create({
  baseURL: process.env.VUE_APP_API_BASE_URL, // 关键：使用环境变量
  timeout: 10000,
});

export default apiClient;
