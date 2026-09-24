import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';

export const useUser = () => {
  return useQuery({
    queryKey: ['user'],
    queryFn: async () => {
      if (!localStorage.getItem('access_token')) return null;
      const { data } = await api.get('/auth/me');
      return data;
    },
    // Don't retry on failed auth
    retry: false 
  });
};

export const useGoogleAuthStatus = () => {
  return useQuery({
    queryKey: ['google-auth-status'],
    queryFn: async () => {
      const { data } = await api.get('/auth/google/status');
      return data;
    },
    staleTime: Infinity,
    retry: false,
  });
};

export const useLogin = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (credentials: any) => {
      const { data } = await api.post('/auth/login', credentials);
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user'] });
    }
  });
};

export const useRegister = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (credentials: any) => {
      const { data } = await api.post('/auth/register', credentials);
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user'] });
    }
  });
};

export const useLogout = () => {
  const queryClient = useQueryClient();
  
  return () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    queryClient.setQueryData(['user'], null);
    window.location.href = '/login';
  };
};
