import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { HUMAN_INPUT } from '../api/paths';

interface HumanInputTaskWidgetProps {
  taskId: string;
}

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

const HumanInputTaskWidget: React.FC<HumanInputTaskWidgetProps> = ({ taskId }) => {
  const [request, setRequest] = useState<HumanInputRequest | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (taskId) {
      fetchHumanInputRequest();
    }
  }, [taskId]);

  const fetchHumanInputRequest = async () => {
    try {
      setLoading(true);
      const response = await fetch(HUMAN_INPUT.GET_BY_TASK(taskId));
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      const requests = data.requests || [];
      // Get the most recent request for this task
      if (requests.length > 0) {
        setRequest(requests[0]);
      } else {
        setRequest(null);
      }
    } catch (err) {
      console.error('Error fetching human input request for task:', err);
      setError('Failed to fetch human input request for task');
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const statusMap: Record<string, { bg: string; label: string }> = {
      pending: { bg: 'bg-yellow-100 text-yellow-800', label: 'Pending' },
      submitted: { bg: 'bg-blue-100 text-blue-800', label: 'Submitted' },
      rejected: { bg: 'bg-red-100 text-red-800', label: 'Rejected' },
      expired: { bg: 'bg-gray-100 text-gray-800', label: 'Expired' },
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
      choice: { bg: 'bg-indigo-100 text-indigo-800', label: 'Choice' },
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
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-700 text-sm">{error}</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 flex justify-center">
        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (!request) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <p className="text-gray-600 text-sm">No human input required for this task</p>
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-xs">
      <div className="flex justify-between items-start mb-2">
        <h4 className="font-medium text-gray-900 text-sm">Human Input Required</h4>
        <div className="flex gap-1">
          {getStatusBadge(request.status)}
          {getTypeBadge(request.input_type)}
        </div>
      </div>
      
      <p className="text-sm text-gray-700 mb-2">{request.description || request.title}</p>
      
      <div className="text-xs text-gray-500 mb-3">
        <div>Created: {new Date(request.created_at).toLocaleDateString()}</div>
        {request.submitted_at && (
          <div>Submitted: {new Date(request.submitted_at).toLocaleDateString()}</div>
        )}
      </div>
      
      {request.status === 'pending' && (
        <Link 
          to={`/human-input`} 
          className="inline-block px-3 py-1.5 bg-blue-500 text-white text-xs rounded-sm hover:bg-blue-600 transition"
        >
          Process Request
        </Link>
      )}
      
      {request.status === 'submitted' && (
        <div className="text-xs text-blue-600">✓ Submitted</div>
      )}
      
      {request.status === 'rejected' && (
        <div className="text-xs text-red-600">✗ Rejected</div>
      )}
    </div>
  );
};

export default HumanInputTaskWidget;