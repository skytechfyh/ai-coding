/** Database connection types */

export interface Column {
  name: string;
  dataType: string;
  isNullable: boolean;
  isPrimaryKey: boolean;
  defaultValue?: string;
}

export interface TableMetadata {
  name: string;
  type: "table" | "view";
  columns: Column[];
}

export interface DatabaseInfo {
  name: string;
  databaseType: string;
  createdAt: string;
  lastUsedAt?: string;
}

export interface DatabaseWithMetadata extends DatabaseInfo {
  tables: TableMetadata[];
}

export interface QueryResult {
  columns: string[];
  rows: Record<string, unknown>[];
  totalRows: number;
  queryTime: number;
}

export interface NaturalLanguageResult {
  sql: string;
  needsConfirmation: boolean;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  errorMessage: string | null;
}

export interface DatabaseListResponse {
  databases: DatabaseInfo[];
}

export interface QueryTab {
  id: string;
  name: string;
  sql: string;
  isDirty: boolean;
}
