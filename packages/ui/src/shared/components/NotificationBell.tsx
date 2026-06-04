import { useState, useEffect } from 'react';
import { HUMAN_REVIEW } from '../api/paths';
import { useNavigate } from 'react-router-dom';
import { Bell } from 'lucide-react';
import { Button } from '@/shared/components/ui/button';
import { Badge } from '@/shared/components/ui/badge';
import { Separator } from '@/shared/components/ui/separator';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/shared/components/ui/dropdown-menu';

interface Props {
  placement?: 'header' | 'sidebar'
}

export default function NotificationBell({ placement = 'header' }: Props) {
  const navigate = useNavigate();
  const [notificationCount, setNotificationCount] = useState(0);
  const [recentNotifications, setRecentNotifications] = useState<any[]>([]);

  // Fetch notifications every 30 seconds
  useEffect(() => {
    let intervalId: ReturnType<typeof setInterval> | null = null;
    
    const fetchNotifications = async () => {
      try {
        const response = await fetch(HUMAN_REVIEW.GET_STATS);
        if (response.ok) {
          const data = await response.json();
          const totalCount = (data.disputed_count || 0) + (data.waiting_human_count || 0) + (data.pending_count || 0);
          setNotificationCount(totalCount);
          setRecentNotifications(data.recent_pending || data.recent || []);
        }
      } catch {
        // silent
      }
    };

    fetchNotifications();
    intervalId = setInterval(fetchNotifications, 30000);
    return () => { if (intervalId) clearInterval(intervalId); };
  }, []);

  const handleNotificationClick = (item: any) => {
    const tabMap: Record<string, string> = { disputed: 'disputed', waiting_human: 'approval', pending_assist: 'assist' };
    const tab = tabMap[item.type] || 'all';
    navigate(`/rulings?tab=${tab}`);
  };

  const getTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      disputed: '争议',
      waiting_human: '等待',
      pending_assist: '协助',
    };
    return labels[type] || '待处理';
  };

  if (placement === 'sidebar') {
    return (
      <div className="p-2 flex-shrink-0">
        <Separator className="mb-2" />
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="w-full relative">
              <Bell size={18} />
              {notificationCount > 0 && (
                <Badge 
                  variant="destructive" 
                  className="absolute -top-1 -right-1 h-5 w-5 p-0 flex items-center justify-center text-xs rounded-full min-w-[20px] min-h-[20px]"
                >
                  {notificationCount > 99 ? '99+' : notificationCount}
                </Badge>
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-80">
            <div className="px-3 py-2 border-b">
              <div className="font-semibold">待处理事项</div>
              <div className="text-xs text-muted-foreground">{recentNotifications.length} 条</div>
            </div>
            {recentNotifications.length > 0 ? (
              recentNotifications.slice(0, 5).map((item: any) => (
                <DropdownMenuItem
                  key={item.id}
                  className="cursor-pointer"
                  onClick={() => handleNotificationClick(item)}
                >
                  <div className="flex flex-col gap-1 w-full">
                    <div className="flex justify-between items-start">
                      <div className="font-medium text-sm truncate">{item.title}</div>
                      <Badge variant="secondary" className="ml-2 shrink-0">
                        {getTypeLabel(item.type)}
                      </Badge>
                    </div>
                    <div className="text-xs text-muted-foreground line-clamp-1">{item.description}</div>
                    <div className="text-xs text-muted-foreground">
                      {new Date(item.created_at).toLocaleDateString('zh-CN')}
                    </div>
                  </div>
                </DropdownMenuItem>
              ))
            ) : (
              <div className="p-4 text-center text-muted-foreground text-sm">暂无待处理事项</div>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    );
  }

  // Header placement
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="relative">
          <Bell size={20} />
          {notificationCount > 0 && (
            <Badge 
              variant="destructive" 
              className="absolute -top-1 -right-1 h-5 w-5 p-0 flex items-center justify-center text-xs rounded-full min-w-[20px] min-h-[20px]"
            >
              {notificationCount > 99 ? '99+' : notificationCount}
            </Badge>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <div className="px-3 py-2 border-b">
          <div className="font-semibold">待处理事项</div>
          <div className="text-xs text-muted-foreground">{notificationCount} 条</div>
        </div>
        {recentNotifications.length > 0 ? (
          recentNotifications.slice(0, 5).map((item: any) => (
            <DropdownMenuItem
              key={item.id}
              className="cursor-pointer"
              onClick={() => handleNotificationClick(item)}
            >
              <div className="flex flex-col gap-1 w-full">
                <div className="flex justify-between items-start">
                  <div className="font-medium text-sm truncate">{item.title}</div>
                  <Badge variant="secondary" className="ml-2 shrink-0">
                    {getTypeLabel(item.type)}
                  </Badge>
                </div>
                <div className="text-xs text-muted-foreground line-clamp-1">{item.description}</div>
                <div className="text-xs text-muted-foreground">
                  {new Date(item.created_at).toLocaleDateString('zh-CN')}
                </div>
              </div>
            </DropdownMenuItem>
          ))
        ) : (
          <div className="p-4 text-center text-muted-foreground text-sm">暂无待处理事项</div>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
