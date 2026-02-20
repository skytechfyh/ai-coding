export type TicketStatus = 'pending' | 'completed';

export interface Ticket {
  id: number;
  title: string;
  description: string | null;
  status: TicketStatus;
  tags: Tag[];
  created_at: string;
  updated_at: string;
}

export interface Tag {
  id: number;
  name: string;
  color: string;
  created_at: string;
}

export interface CreateTicketRequest {
  title: string;
  description?: string;
  tag_ids?: number[];
}

export interface UpdateTicketRequest {
  title?: string;
  description?: string;
  status?: TicketStatus;
  tag_ids?: number[];
}

export interface CreateTagRequest {
  name: string;
  color?: string;
}

export interface UpdateTagRequest {
  name?: string;
  color?: string;
}

export interface AddTagToTicketRequest {
  tag_id: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
  error?: {
    code: string;
    message: string;
  };
}

export interface TicketQueryParams {
  tag_id?: number;
  status?: TicketStatus;
  search?: string;
  page?: number;
  page_size?: number;
}

export const TAG_COLORS = [
  '#EF4444', '#F97316', '#F59E0B', '#84CC16', '#22C55E',
  '#10B981', '#14B8A6', '#06B6D4', '#0EA5E9', '#3B82F6',
  '#6366F1', '#8B5CF6', '#A855F7', '#D946EF', '#EC4899', '#6B7280',
] as const;
