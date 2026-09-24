/* eslint-disable react-refresh/only-export-components */
import React from 'react';
import { createBrowserRouter, Navigate, useRouteError } from 'react-router-dom';
import Login from '../pages/Login';
import Register from '../pages/Register';
import Dashboard from '../pages/Dashboard';
import ChatPage from '../pages/Chat';
import { ErrorFallback } from '../components/ErrorFallback';

function AuthWrapper({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('access_token');
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function RouteError() {
  const error = useRouteError() as any;
  const message = error?.message || error?.statusText || 'Something went wrong while loading this page.';
  return (
    <ErrorFallback
      error={{ message }}
      resetErrorBoundary={() => { window.location.href = '/'; }}
    />
  );
}

export const router = createBrowserRouter([
  { path: '/login',    element: <Login />, errorElement: <RouteError /> },
  { path: '/register', element: <Register />, errorElement: <RouteError /> },
  {
    path: '/',
    element: <AuthWrapper><Dashboard /></AuthWrapper>,
    errorElement: <RouteError />,
  },
  {
    path: '/chat/:chatId',
    element: <AuthWrapper><ChatPage /></AuthWrapper>,
    errorElement: <RouteError />,
  },
]);
