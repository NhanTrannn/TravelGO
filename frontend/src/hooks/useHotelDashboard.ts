/**
 * Custom Hook for B2B Hotel Dashboard
 * Quản lý authentication và data fetching cho hotel business
 */
import { useState, useEffect, useCallback } from 'react';

// Types
interface User {
  user_id: string;
  username: string;
  hotel_id: string;
  role: string;
}

interface Hotel {
  _id: string;
  name: string;
  address: string;
  config: {
    currency: string;
    competitors: string[];
  };
}

interface KPIStats {
  total: number;
  positive: number;
  negative: number;
  neutral: number;
  avg_sentiment_score: number;
}

interface PainPoint {
  cluster_name: string;
  severity: 'High' | 'Medium' | 'Low';
  volume: number;
  representative_quotes: string[];
  action_plan: string;
}

interface Review {
  _id: string;
  source: string;
  original_text: string;
  review_date: string;
  rating?: number;
  ai_analysis: {
    sentiment: 'Positive' | 'Negative' | 'Neutral';
    sentiment_score: number;
    aspects: string[];
    keywords: string[];
  };
}

interface DashboardData {
  hotel_info: Hotel | null;
  kpi_stats: KPIStats;
  pain_points: PainPoint[];
  recent_reviews: Review[];
  last_updated: string;
}

interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  hotel: Hotel | null;
  token: string | null;
}

// API Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

/**
 * Hook for authentication
 */
export const useB2BAuth = () => {
  const [authState, setAuthState] = useState<AuthState>({
    isAuthenticated: false,
    user: null,
    hotel: null,
    token: null,
  });
  const [loading, setLoading] = useState(true);

  // Load auth state from localStorage on mount
  useEffect(() => {
    const token = localStorage.getItem('b2b_token');
    const user = localStorage.getItem('b2b_user');
    const hotel = localStorage.getItem('b2b_hotel');

    if (token && user && hotel) {
      setAuthState({
        isAuthenticated: true,
        user: JSON.parse(user),
        hotel: JSON.parse(hotel),
        token,
      });
    }
    
    setLoading(false);
  }, []);

  const login = async (username: string, password: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/b2b/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Login failed');
      }

      const data = await response.json();

      // Save to localStorage
      localStorage.setItem('b2b_token', data.access_token);
      localStorage.setItem('b2b_user', JSON.stringify(data.user));
      localStorage.setItem('b2b_hotel', JSON.stringify(data.hotel));

      setAuthState({
        isAuthenticated: true,
        user: data.user,
        hotel: data.hotel,
        token: data.access_token,
      });

      return { success: true };
    } catch (error) {
      console.error('Login error:', error);
      return { 
        success: false, 
        error: error instanceof Error ? error.message : 'Unknown error' 
      };
    }
  };

  const logout = useCallback(() => {
    localStorage.removeItem('b2b_token');
    localStorage.removeItem('b2b_user');
    localStorage.removeItem('b2b_hotel');

    setAuthState({
      isAuthenticated: false,
      user: null,
      hotel: null,
      token: null,
    });
  }, []);

  return {
    ...authState,
    loading,
    login,
    logout,
  };
};

/**
 * Hook for fetching dashboard data
 */
export const useHotelDashboard = () => {
  const { isAuthenticated, token, user, hotel } = useB2BAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<DashboardData>({
    hotel_info: null,
    kpi_stats: {
      total: 0,
      positive: 0,
      negative: 0,
      neutral: 0,
      avg_sentiment_score: 0,
    },
    pain_points: [],
    recent_reviews: [],
    last_updated: new Date().toISOString(),
  });

  const fetchDashboardData = useCallback(async () => {
    if (!isAuthenticated || !token) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE_URL}/api/b2b/dashboard`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch dashboard: ${response.statusText}`);
      }

      const result = await response.json();
      setData(result);
    } catch (err) {
      console.error('Dashboard fetch error:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch dashboard data');
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, token]);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  return {
    data,
    loading,
    error,
    user,
    hotel,
    refresh: fetchDashboardData,
  };
};

/**
 * Hook for fetching reviews with filters
 */
export const useHotelReviews = (
  page: number = 1,
  pageSize: number = 20,
  sentiment?: string,
  days?: number
) => {
  const { isAuthenticated, token } = useB2BAuth();
  const [loading, setLoading] = useState(true);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    if (!isAuthenticated || !token) {
      setLoading(false);
      return;
    }

    const fetchReviews = async () => {
      try {
        setLoading(true);

        const params = new URLSearchParams({
          page: page.toString(),
          page_size: pageSize.toString(),
        });

        if (sentiment) params.append('sentiment', sentiment);
        if (days) params.append('days', days.toString());

        const response = await fetch(
          `${API_BASE_URL}/api/b2b/reviews?${params.toString()}`,
          {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          }
        );

        if (!response.ok) {
          throw new Error('Failed to fetch reviews');
        }

        const data = await response.json();
        setReviews(data.reviews);
        setTotal(data.total);
      } catch (error) {
        console.error('Reviews fetch error:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchReviews();
  }, [isAuthenticated, token, page, pageSize, sentiment, days]);

  return { reviews, total, loading };
};

/**
 * Hook for fetching pain points
 */
export const usePainPoints = () => {
  const { isAuthenticated, token } = useB2BAuth();
  const [loading, setLoading] = useState(true);
  const [painPoints, setPainPoints] = useState<PainPoint[]>([]);
  const [summary, setSummary] = useState('');

  useEffect(() => {
    if (!isAuthenticated || !token) {
      setLoading(false);
      return;
    }

    const fetchPainPoints = async () => {
      try {
        setLoading(true);

        const response = await fetch(`${API_BASE_URL}/api/b2b/pain-points`, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (!response.ok) {
          throw new Error('Failed to fetch pain points');
        }

        const data = await response.json();
        
        // Transform API response to PainPoint format
        const transformedPainPoints: PainPoint[] = [];
        
        // Use key_findings as pain points
        if (data.key_findings && Array.isArray(data.key_findings)) {
          data.key_findings.forEach((finding: string, index: number) => {
            const recommendation = data.recommendations?.[index];
            transformedPainPoints.push({
              cluster_name: recommendation?.title || `Pain Point ${index + 1}`,
              severity: recommendation?.priority === 'RẤT CAO' ? 'High' : 'Medium',
              volume: data.sentiment_summary?.Negative || 0,
              representative_quotes: [finding],
              action_plan: recommendation?.description || finding
            });
          });
        }
        
        setPainPoints(transformedPainPoints);
        setSummary(data.query || '');
      } catch (error) {
        console.error('Pain points fetch error:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchPainPoints();
  }, [isAuthenticated, token]);

  return { painPoints, summary, loading };
};
