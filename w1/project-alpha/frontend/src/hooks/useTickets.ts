import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../lib/api';
import { Ticket, CreateTicketRequest, UpdateTicketRequest, TicketQueryParams } from '../types';

export function useTickets(params: TicketQueryParams = {}) {
  return useQuery({
    queryKey: ['tickets', params],
    queryFn: async () => {
      try {
        const result: any = await api.get('/tickets', { params });
        if (result.success && result.data) {
          return result.data;
        }
        return { items: [], total: 0, page: 1, page_size: 20 };
      } catch (error) {
        console.error('Failed to fetch tickets:', error);
        return { items: [], total: 0, page: 1, page_size: 20 };
      }
    },
  });
}

export function useTicket(id: number) {
  return useQuery({
    queryKey: ['ticket', id],
    queryFn: async () => {
      const response = await api.get<{ success: boolean; data: Ticket }>(`/tickets/${id}`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useCreateTicket() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: CreateTicketRequest) => {
      const response = await api.post<{ success: boolean; data: Ticket }>('/tickets', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tickets'] });
    },
  });
}

export function useUpdateTicket() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: number; data: UpdateTicketRequest }) => {
      const response = await api.put<{ success: boolean; data: Ticket }>(`/tickets/${id}`, data);
      return response.data;
    },
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['tickets'] });
      queryClient.invalidateQueries({ queryKey: ['ticket', id] });
    },
  });
}

export function useDeleteTicket() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/tickets/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tickets'] });
    },
  });
}

export function useCompleteTicket() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const response = await api.patch<{ success: boolean; data: Ticket }>(`/tickets/${id}/complete`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tickets'] });
    },
  });
}

export function useUncompleteTicket() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const response = await api.patch<{ success: boolean; data: Ticket }>(`/tickets/${id}/uncomplete`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tickets'] });
    },
  });
}
