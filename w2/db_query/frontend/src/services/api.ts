/** API service for communicating with the backend */
import axios from "axios";

import type {
  ApiResponse,
  DatabaseListResponse,
  DatabaseWithMetadata,
  QueryResult,
  NaturalLanguageResult,
} from "../types";

const api = axios.create({
  baseURL: "/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
});

export const apiService = {
  /** Get all saved database connections */
  async listDatabases(): Promise<DatabaseListResponse> {
    const response = await api.get<DatabaseListResponse>("/dbs");
    return response.data;
  },

  /** Add a new database connection */
  async createDatabase(name: string, url: string): Promise<void> {
    const response = await api.put<ApiResponse<{ name: string; databaseType: string }>>(
      `/dbs/${name}`,
      { url }
    );
    if (!response.data.success) {
      throw new Error(response.data.errorMessage || "Failed to create database");
    }
  },

  /** Get database metadata (tables and columns) */
  async getDatabase(name: string): Promise<DatabaseWithMetadata> {
    const response = await api.get<ApiResponse<DatabaseWithMetadata>>(`/dbs/${name}`);
    if (!response.data.success) {
      throw new Error(response.data.errorMessage || "Failed to get database");
    }
    return response.data.data!;
  },

  /** Delete a database connection */
  async deleteDatabase(name: string): Promise<void> {
    const response = await api.delete<ApiResponse<null>>(`/dbs/${name}`);
    if (!response.data.success) {
      throw new Error(response.data.errorMessage || "Failed to delete database");
    }
  },

  /** Execute a SQL query */
  async executeQuery(name: string, sql: string): Promise<QueryResult> {
    const response = await api.post<ApiResponse<QueryResult>>(`/dbs/${name}/query`, {
      sql,
    });
    if (!response.data.success) {
      throw new Error(response.data.errorMessage || "Failed to execute query");
    }
    return response.data.data!;
  },

  /** Generate SQL from natural language */
  async generateSql(name: string, prompt: string): Promise<NaturalLanguageResult> {
    const response = await api.post<ApiResponse<NaturalLanguageResult>>(
      `/dbs/${name}/query/natural`,
      { prompt }
    );
    if (!response.data.success) {
      throw new Error(response.data.errorMessage || "Failed to generate SQL");
    }
    return response.data.data!;
  },
};
