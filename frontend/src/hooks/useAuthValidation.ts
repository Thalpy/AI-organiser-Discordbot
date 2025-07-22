// Hook for validating authentication state

import { useEffect, useState } from 'react';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { loginSuccess, loginFailure, selectAuthToken } from '../store/slices/authSlice';

export const useAuthValidation = () => {
  const dispatch = useAppDispatch();
  const token = useAppSelector(selectAuthToken);
  const [isValidating, setIsValidating] = useState(!!token);

  useEffect(() => {
    const validateToken = async () => {
      if (!token) {
        setIsValidating(false);
        return;
      }

      try {
        // Validate token with the server
        const response = await fetch('/api/v1/auth/profile', {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (response.ok) {
          const user = await response.json();
          dispatch(loginSuccess({ user, token }));
        } else {
          // Token is invalid
          dispatch(loginFailure('Session expired'));
        }
      } catch (error) {
        console.error('Token validation failed:', error);
        dispatch(loginFailure('Authentication failed'));
      } finally {
        setIsValidating(false);
      }
    };

    validateToken();
  }, [token, dispatch]);

  return { isValidating };
};