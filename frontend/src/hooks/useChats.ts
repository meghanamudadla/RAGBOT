import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';

export const useChats = () => {
  return useQuery({
    queryKey: ['chats'],
    queryFn: async () => {
      const { data } = await api.get('/chat/');
      return data;
    },
  });
};

export const useCreateChat = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (title: string = 'New Chat') => {
      const { data } = await api.post('/chat/', { title });
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['chats'] }),
  });
};

export const useDeleteChat = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/chat/${id}`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['chats'] }),
  });
};

export const useRenameChat = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, title }: { id: string; title: string }) => {
      const { data } = await api.patch(`/chat/${id}`, { title });
      return data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['chats'] });
      queryClient.invalidateQueries({ queryKey: ['chat', variables.id] });
    },
  });
};


export const useChatMessages = (chatId: string) => {
  return useQuery({
    queryKey: ['chat', chatId],
    queryFn: async () => {
      const { data } = await api.get(`/chat/${chatId}`);
      return data;
    },
    enabled: !!chatId,
  });
};

export const useSendMessage = (chatId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (content: string) => {
      const { data } = await api.post(`/chat/${chatId}/message`, { content });
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['chat', chatId] }),
  });
};
