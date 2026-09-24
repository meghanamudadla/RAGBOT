import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RouterProvider } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { ErrorBoundary } from 'react-error-boundary';
import { router } from './routes';
import { ErrorFallback } from './components/ErrorFallback';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Toaster 
        position="bottom-right" 
        toastOptions={{
          style: {
            background: '#1e293b', // Tailwind slate-800
            color: '#f8fafc',      // Tailwind slate-50
            border: '1px solid #334155' // Tailwind slate-700
          },
          error: {
            iconTheme: {
              primary: '#ef4444', // red-500
              secondary: '#fff',
            }
          }
        }} 
      />
      <ErrorBoundary FallbackComponent={ErrorFallback}>
        <RouterProvider router={router} />
      </ErrorBoundary>
    </QueryClientProvider>
  );
}

export default App;
