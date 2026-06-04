import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { HUMAN_INPUT } from '../api/paths';

interface HumanInputRequest {
  id: string;
  task_id: string;
  title: string;
  description: string;
  input_type: string;
  status: string;
  created_at: string;
  updated_at: string;
  submitted_at?: string;
  submitted_by?: string;
  input_data?: any;
  context?: any;
}

interface HumanInputWidgetProps {
  limit?: number;
}

const HumanInputWidget: React.FC<HumanInputWidgetProps> = ({ limit = 5 }) => {
  const [requests, setRequests] = useState<HumanInputRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchHumanInputRequests();
  }, []);

  const fetchHumanInputRequests = async () => {
    try {
      setLoading(true);
      const response = await fetch(HUMAN_INPUT.LIST_PENDING);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      const requestsList = Array.isArray(data) ? data : data.requests || [];
      const limitedRequests = limit ? requestsList.slice(0, limit) : requestsList;
      setRequests(limitedRequests);
    } catch (err) {
      console.error('Error fetching human input requests:', err);
      setError('Failed to fetch human input requests');
    } finally {
      setLoading(false);
    }
  };

  const refreshData = () => {
    fetchHumanInputRequests();
  };

  const getStatusBadge = (status: string) => {
    const statusMap: Record<string, { bg: string; label: string }> = {
      pending: { bg: 'bg-yellow-100 text-yellow-800', label: 'Pending' },
      submitted: { bg: 'bg-blue-100 text-blue-800', label: 'Submitted' },
      rejected: { bg: 'bg-red-100 text-red-800', label: 'Rejected' },
    };
    const config = statusMap[status] || { bg: 'bg-gray-100 text-gray-800', label: status };
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.bg}`}>
        {config.label}
      </span>
    );
  };

  const getTypeBadge = (inputType: string) => {
    const typeMap: Record<string, { bg: string; label: string }> = {
      confirmation: { bg: 'bg-purple-100 text-purple-800', label: 'Confirmation' },
      approval: { bg: 'bg-green-100 text-green-800', label: 'Approval' },
      input: { bg: 'bg-blue-100 text-blue-800', label: 'Input' },
    };
    const config = typeMap[inputType] || { bg: 'bg-gray-100 text-gray-800', label: inputType };
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.bg}`}>
        {config.label}
      </span>
    );
  };

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-gray-800">Human Input Requests</h3>
          <button onClick={refreshData} className="text-gray-500 hover:text-gray-700">
            Refresh
          </button>
        </div>
        <p className="text-red-500">{error}</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-800">Human Input Requests</h3>
        <button onClick={refreshData} className="text-gray-500 hover:text-gray-700">
          Refresh
        </button>
      </div>
      
      {loading ? (
        <div className="flex justify-center items-center h-32">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
        </div>
      ) : requests.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <p>No pending human input requests</p>
        </div>
      ) : (
        <div className="space-y-3">
          {requests.map((request) => (
            <div key={request.id} className="border rounded-lg p-3 hover:shadow-md transition-shadow">
              <div className="flex justify-between items-start">
                <div className="flex-1 min-w-0">
                  <h4 className="font-medium text-gray-900 truncate">{request.title}</h4>
                  <p className="text-sm text-gray-500 truncate">{request.description}</p>
                  <div className="flex items-center gap-2 mt-2">
                    {getStatusBadge(request.status)}
                    {getTypeBadge(request.input_type)}
                  </div>
                </div>
                <div className="text-right text-xs text-gray-400 ml-2">
                  <div>{new Date(request.created_at).toLocaleDateString()}</div>
                  <div className="font-mono">{request.id.substring(0, 8)}...</div>
                </div>
              </div>
              <div className="mt-2 flex justify-end">
                <Link to="/human-input" className="text-sm text-blue-600 hover:text-blue-800">
                  View Details
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
      
      {requests.length > 0 && (
        <div className="mt-4 text-center">
          <Link to="/human-input" className="text-sm font-medium text-blue-600 hover:text-blue-800">
            View All Requests
          </Link>
        </div>
      )}
    </div>
  );
};

export default HumanInputWidget;