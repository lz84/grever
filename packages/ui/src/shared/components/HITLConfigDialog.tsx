import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/shared/components/ui/dialog';
import { Button } from '@/shared/components/ui/button';
import { Input } from '@/shared/components/ui/input';
import { Label } from '@/shared/components/ui/label';
import { Textarea } from '@/shared/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/components/ui/select';

// HITL Input Types and Configurations
const HITL_CONFIGS: Record<string, { label: string; description: string; input_type: string }> = {
  ai_approval: {
    label: '审批',
    description: '人工审批配置',
    input_type: 'approval',
  },
  ai_data: {
    label: '数据',
    description: '数据录入配置',
    input_type: 'data_entry',
  },
  ai_confirm: {
    label: '确认',
    description: '确认配置',
    input_type: 'confirmation',
  },
};

interface HITLConfig {
  title?: string;
  description?: string;
  timeout_minutes?: number;
  default_value?: string;
  timeout_action?: string;
  approvers?: string[];
  input_type?: string;
}

interface HITLConfigDialogProps {
  open: boolean;
  onOpenChange?: (open: boolean) => void;  // Alternative interface
  executorType?: string;
  initialData?: HITLConfig;
  onSave: (config: HITLConfig) => void;
  // TaskDetail interface
  taskTitle?: string;
  onClose?: () => void;
}

const HITLConfigDialog: React.FC<HITLConfigDialogProps> = ({
  open,
  onOpenChange,
  executorType,
  initialData,
  onSave,
  taskTitle,
  onClose,
}) => {
  // Use either interface
  const handleClose = onClose || ((open: boolean) => onOpenChange?.(!open));
  const effectiveExecutorType = executorType || 'ai_approval'; // Default to approval for TaskDetail

  const [config, setConfig] = useState<HITLConfig>({
    title: taskTitle ? `人工审批: ${taskTitle}` : (initialData?.title || ''),
    description: initialData?.description || '',
    timeout_minutes: initialData?.timeout_minutes || 30,
    default_value: initialData?.default_value || '',
    timeout_action: initialData?.timeout_action || 'use_default',
    approvers: initialData?.approvers || [],
    input_type: effectiveExecutorType in HITL_CONFIGS ? HITL_CONFIGS[effectiveExecutorType].input_type : 'approval',
  });

  useEffect(() => {
    // Reset form when dialog opens or executor type changes
    if (open) {
      setConfig({
        title: taskTitle ? `人工审批: ${taskTitle}` : (initialData?.title || ''),
        description: initialData?.description || '',
        timeout_minutes: initialData?.timeout_minutes || 30,
        default_value: initialData?.default_value || '',
        timeout_action: initialData?.timeout_action || 'use_default',
        approvers: initialData?.approvers || [],
        input_type: effectiveExecutorType in HITL_CONFIGS ? HITL_CONFIGS[effectiveExecutorType].input_type : 'approval',
      });
    }
  }, [open, executorType, initialData, taskTitle]);

  const handleSubmit = () => {
    onSave(config);
    handleClose(false);
  };

  const cancelHandler = () => {
    handleClose(false);
  };

  const executorTypeInfo = effectiveExecutorType in HITL_CONFIGS ? HITL_CONFIGS[effectiveExecutorType] : null;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {executorTypeInfo ? executorTypeInfo.label : 'HITL 配置'}
          </DialogTitle>
          <DialogDescription>
            {executorTypeInfo ? executorTypeInfo.description : '请配置人工交互参数'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-2">
          {/* Basic Info */}
          <div className="space-y-3">
            <Label htmlFor="title">标题 *</Label>
            <Input
              id="title"
              value={config.title}
              onChange={(e) => setConfig({ ...config, title: e.target.value })}
              placeholder="请输入标题"
              className="h-9 text-sm"
            />
          </div>

          <div className="space-y-3">
            <Label htmlFor="description">说明</Label>
            <Textarea
              id="description"
              value={config.description}
              onChange={(e) => setConfig({ ...config, description: e.target.value })}
              placeholder="请输入详细说明..."
              rows={3}
              className="text-sm"
            />
          </div>

          {/* Timeout Configuration */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-3">
              <Label htmlFor="timeout_minutes">超时(分钟)</Label>
              <Input
                id="timeout_minutes"
                type="number"
                min={1}
                max={1440}
                value={config.timeout_minutes}
                onChange={(e) => setConfig({ ...config, timeout_minutes: parseInt(e.target.value) || 30 })}
                className="h-9 text-sm"
              />
            </div>
            <div className="space-y-3">
              <Label htmlFor="timeout_action">超时动作</Label>
              <Select
                value={config.timeout_action}
                onValueChange={(v) => setConfig({ ...config, timeout_action: v })}
              >
                <SelectTrigger className="h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="use_default">使用默认值</SelectItem>
                  <SelectItem value="abort">中止</SelectItem>
                  <SelectItem value="retry">重试</SelectItem>
                  <SelectItem value="escalate">升级</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Default Value (for data entry) */}
          {effectiveExecutorType === 'ai_data' && (
            <div className="space-y-3">
              <Label htmlFor="default_value">默认值</Label>
              <Input
                id="default_value"
                value={config.default_value}
                onChange={(e) => setConfig({ ...config, default_value: e.target.value })}
                placeholder="默认输入值"
                className="h-9 text-sm"
              />
            </div>
          )}

          {/* Approvers (for approval) */}
          {effectiveExecutorType === 'ai_approval' && (
            <div className="space-y-3">
              <Label htmlFor="approvers">审批人（逗号分隔）</Label>
              <Input
                id="approvers"
                value={config.approvers?.join(', ')}
                onChange={(e) =>
                  setConfig({
                    ...config,
                    approvers: e.target.value
                      .split(',')
                      .map(s => s.trim())
                      .filter(Boolean),
                  })
                }
                placeholder="user1@example.com, user2@example.com"
                className="h-9 text-sm"
              />
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={cancelHandler} type="button">
            取消
          </Button>
          <Button onClick={handleSubmit} type="button" disabled={!config.title?.trim()}>
            保存配置
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default HITLConfigDialog;
