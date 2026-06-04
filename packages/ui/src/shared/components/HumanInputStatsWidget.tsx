import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

interface HumanInputStats {
  total: number;
  pending: number;
  submitted: number;
  rejected: number;
  expired: number;
  byType: Record<string, number>;
  byPriority: Record<string, number>;
}

const HumanInputStatsWidget: React.FC = () => {
  const [stats, setStats] = useState<HumanInputStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // In a real application, this would fetch from the API
      // For now, we'll simulate with mock data
      const mockStats: HumanInputStats = {
        total: 42,
        pending: 12,
        submitted: 25,
        rejected: 3,
        expired: 2,
        byType: {
          approval: 18,
          confirmation: 15,
          input: 6,
          choice: 3
        },
        byPriority: {
          high: 8,
          medium: 22,
          low: 12
        }
      };
      
      // Simulate API call
      setTimeout(() => {
        setStats(mockStats);
        setLoading(false);
      }, 500);
      
      // Uncomment when API is available:
      /*
      const response = await fetch('/api/v1/human-input/stats');
      if (!response.ok) {
        throw new Error('Failed to fetch stats');
      }
      const data = await response.json();
      setStats(data);
      */
    } catch (err) {
      console.error('Error fetching human input stats:', err);
      setError('Failed to load statistics');
      setLoading(false);
    }
  };

  const refreshStats = () => {
    fetchStats();
  };

  const getTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      approval: '审批',
      confirmation: '确认',
      input: '输入',
      choice: '选择',
    };
    return labels[type] || type;
  };

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="font-semibold text-gray-900">人类输入统计</h3>
          <button 
            onClick={refreshStats}
            className="text-gray-400 hover:text-gray-600"
          >
            ↻
          </button>
        </div>
        <p className="text-red-600 text-sm">{error}</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="font-semibold text-gray-900">人类输入统计</h3>
          <button 
            onClick={refreshStats}
            className="text-gray-400 hover:text-gray-600"
          >
            ↻
          </button>
        </div>
        <div className="flex justify-center items-center h-32">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
        </div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="font-semibold text-gray-900">人类输入统计</h3>
          <button 
            onClick={refreshStats}
            className="text-gray-400 hover:text-gray-600"
          >
            ↻
          </button>
        </div>
        <p className="text-gray-500 text-sm">暂无数据</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm">
      <div className="p-4 border-b">
        <div className="flex justify-between items-center">
          <h3 className="font-semibold text-gray-900">人类输入统计</h3>
          <button 
            onClick={refreshStats}
            className="text-gray-400 hover:text-gray-600 text-sm"
          >
            ↻ 刷新
          </button>
        </div>
        <p className="text-xs text-gray-500">实时统计信息</p>
      </div>
      
      <div className="p-4">
        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="bg-blue-50 rounded-lg p-3 text-center">
            <div className="text-lg font-bold text-blue-700">{stats.total}</div>
            <div className="text-xs text-blue-600">总计</div>
          </div>
          <div className="bg-yellow-50 rounded-lg p-3 text-center">
            <div className="text-lg font-bold text-yellow-700">{stats.pending}</div>
            <div className="text-xs text-yellow-600">待处理</div>
          </div>
          <div className="bg-green-50 rounded-lg p-3 text-center">
            <div className="text-lg font-bold text-green-700">{stats.submitted}</div>
            <div className="text-xs text-green-600">已提交</div>
          </div>
          <div className="bg-red-50 rounded-lg p-3 text-center">
            <div className="text-lg font-bold text-red-700">{stats.rejected}</div>
            <div className="text-xs text-red-600">已拒绝</div>
          </div>
        </div>

        {/* Type Distribution */}
        <div className="mb-4">
          <h4 className="text-sm font-medium text-gray-700 mb-2">类型分布</h4>
          <div className="space-y-2">
            {Object.entries(stats.byType).map(([type, count]) => (
              <div key={type} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                  <span className="text-xs text-gray-600">{getTypeLabel(type)}</span>
                </div>
                <span className="text-xs font-medium text-gray-900">{count}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Priority Distribution */}
        <div className="mb-4">
          <h4 className="text-sm font-medium text-gray-700 mb-2">优先级分布</h4>
          <div className="space-y-2">
            {Object.entries(stats.byPriority).map(([priority, count]) => (
              <div key={priority} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${
                    priority === 'high' ? 'bg-red-500' : 
                    priority === 'medium' ? 'bg-yellow-500' : 'bg-green-500'
                  }`}></div>
                  <span className="text-xs text-gray-600 capitalize">{priority}</span>
                </div>
                <span className="text-xs font-medium text-gray-900">{count}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2">
          <Link 
            to="/human-input" 
            className="flex-1 text-center py-2 bg-blue-500 text-white text-xs rounded-sm hover:bg-blue-600"
          >
            查看详情
          </Link>
          <Link 
            to="/human-input/analytics" 
            className="flex-1 text-center py-2 bg-gray-200 text-gray-700 text-xs rounded-sm hover:bg-gray-300"
          >
            分析报告
          </Link>
        </div>
      </div>
    </div>
  );
};

export default HumanInputStatsWidget;