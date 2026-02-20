import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../lib/api';
import { Tag, CreateTagRequest, UpdateTagRequest } from '../types';

export function useTags() {
  return useQuery({
    queryKey: ['tags'],
    queryFn: async () => {
      try {
        const result: any = await api.get('/tags');
        if (result.success && result.data) {
          return result.data;
        }
        return [];
      } catch (error) {
        console.error('Failed to fetch tags:', error);
        return [];
      }
    },
  });
}

export function useCreateTag() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: CreateTagRequest) => {
      const response = await api.post<{ success: boolean; data: Tag }>('/tags', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tags'] });
    },
  });
}

export function useUpdateTag() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: number; data: UpdateTagRequest }) => {
      const response = await api.put<{ success: boolean; data: Tag }>(`/tags/${id}`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tags'] });
    },
  });
}

export function useDeleteTag() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/tags/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tags'] });
    },
  });
}
