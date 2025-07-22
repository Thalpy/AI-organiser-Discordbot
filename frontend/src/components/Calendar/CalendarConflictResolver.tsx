import React, { useState } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../UI/Card';
import { Button } from '../UI/Button';
import { Badge } from '../UI/Badge';
import { Alert, AlertDescription } from '../UI/Alert';
import {
  AlertTriangle,
  Calendar,
  Clock,
  MapPin,
  FileText,
  CheckCircle,
  ArrowRight,
} from 'lucide-react';

interface CalendarConflict {
  task_id: number;
  calendar_event_id: string;
  conflict_type: string;
  task_updated: string;
  calendar_updated: string;
  task_data: {
    title: string;
    due_time: string | null;
    location: string | null;
  };
  calendar_data: {
    title: string;
    start_time: string;
    end_time: string;
    location: string | null;
  };
}

interface CalendarConflictResolverProps {
  conflicts: CalendarConflict[];
  onResolveConflict: (taskId: number, resolution: string) => Promise<void>;
  onRefresh: () => Promise<void>;
}

export const CalendarConflictResolver: React.FC<CalendarConflictResolverProps> = ({
  conflicts,
  onResolveConflict,
  onRefresh,
}) => {
  const [resolvingConflicts, setResolvingConflicts] = useState<Set<number>>(new Set());

  const handleResolveConflict = async (taskId: number, resolution: string) => {
    setResolvingConflicts(prev => new Set(prev).add(taskId));
    
    try {
      await onResolveConflict(taskId, resolution);
      await onRefresh();
    } catch (error) {
      console.error('Failed to resolve conflict:', error);
    } finally {
      setResolvingConflicts(prev => {
        const newSet = new Set(prev);
        newSet.delete(taskId);
        return newSet;
      });
    }
  };

  const formatDateTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const getConflictTypes = (conflictType: string) => {
    return conflictType.split(',').map(type => type.trim());
  };

  const getConflictBadgeVariant = (type: string) => {
    switch (type) {
      case 'title':
        return 'destructive';
      case 'time':
        return 'destructive';
      case 'location':
        return 'secondary';
      case 'duration':
        return 'secondary';
      default:
        return 'secondary';
    }
  };

  const getConflictIcon = (type: string) => {
    switch (type) {
      case 'title':
        return <FileText className="h-3 w-3" />;
      case 'time':
        return <Clock className="h-3 w-3" />;
      case 'location':
        return <MapPin className="h-3 w-3" />;
      case 'duration':
        return <Clock className="h-3 w-3" />;
      default:
        return <AlertTriangle className="h-3 w-3" />;
    }
  };

  if (conflicts.length === 0) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="text-center space-y-4">
            <CheckCircle className="h-12 w-12 mx-auto text-green-500" />
            <div>
              <h3 className="text-lg font-semibold">No Conflicts</h3>
              <p className="text-muted-foreground">
                All your tasks and calendar events are in sync
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Alert>
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>
          {conflicts.length} sync conflict{conflicts.length !== 1 ? 's' : ''} detected. 
          Please review and resolve them to maintain synchronization.
        </AlertDescription>
      </Alert>

      {conflicts.map((conflict) => (
        <Card key={`${conflict.task_id}-${conflict.calendar_event_id}`}>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">Task #{conflict.task_id}</CardTitle>
              <div className="flex gap-1">
                {getConflictTypes(conflict.conflict_type).map((type) => (
                  <Badge 
                    key={type} 
                    variant={getConflictBadgeVariant(type)}
                    className="flex items-center gap-1"
                  >
                    {getConflictIcon(type)}
                    {type}
                  </Badge>
                ))}
              </div>
            </div>
            <CardDescription>
              Conflict between task and calendar event - choose which version to keep
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Conflict Details */}
            <div className="grid gap-4 md:grid-cols-2">
              {/* Task Data */}
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-blue-500" />
                  <h4 className="font-semibold">Task Data</h4>
                  <Badge variant="outline" className="text-xs">
                    Updated {formatDateTime(conflict.task_updated)}
                  </Badge>
                </div>
                <div className="space-y-2 pl-6">
                  <div>
                    <span className="text-sm text-muted-foreground">Title:</span>
                    <p className="font-medium">{conflict.task_data.title}</p>
                  </div>
                  {conflict.task_data.due_time && (
                    <div>
                      <span className="text-sm text-muted-foreground">Due Time:</span>
                      <p className="font-medium">{formatDateTime(conflict.task_data.due_time)}</p>
                    </div>
                  )}
                  {conflict.task_data.location && (
                    <div>
                      <span className="text-sm text-muted-foreground">Location:</span>
                      <p className="font-medium">{conflict.task_data.location}</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Calendar Data */}
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-green-500" />
                  <h4 className="font-semibold">Calendar Data</h4>
                  <Badge variant="outline" className="text-xs">
                    Updated {formatDateTime(conflict.calendar_updated)}
                  </Badge>
                </div>
                <div className="space-y-2 pl-6">
                  <div>
                    <span className="text-sm text-muted-foreground">Title:</span>
                    <p className="font-medium">{conflict.calendar_data.title}</p>
                  </div>
                  <div>
                    <span className="text-sm text-muted-foreground">Time:</span>
                    <p className="font-medium">
                      {formatDateTime(conflict.calendar_data.start_time)} - {formatDateTime(conflict.calendar_data.end_time)}
                    </p>
                  </div>
                  {conflict.calendar_data.location && (
                    <div>
                      <span className="text-sm text-muted-foreground">Location:</span>
                      <p className="font-medium">{conflict.calendar_data.location}</p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Resolution Actions */}
            <div className="border-t pt-4">
              <h4 className="font-semibold mb-3">Choose Resolution Strategy:</h4>
              <div className="grid gap-2 md:grid-cols-4">
                <Button
                  variant="outline"
                  onClick={() => handleResolveConflict(conflict.task_id, 'task_wins')}
                  disabled={resolvingConflicts.has(conflict.task_id)}
                  className="flex items-center gap-2"
                >
                  <FileText className="h-4 w-4" />
                  Keep Task Data
                </Button>
                
                <Button
                  variant="outline"
                  onClick={() => handleResolveConflict(conflict.task_id, 'calendar_wins')}
                  disabled={resolvingConflicts.has(conflict.task_id)}
                  className="flex items-center gap-2"
                >
                  <Calendar className="h-4 w-4" />
                  Keep Calendar Data
                </Button>
                
                <Button
                  variant="outline"
                  onClick={() => handleResolveConflict(conflict.task_id, 'merge')}
                  disabled={resolvingConflicts.has(conflict.task_id)}
                  className="flex items-center gap-2"
                >
                  <ArrowRight className="h-4 w-4" />
                  Smart Merge
                </Button>
                
                <Button
                  variant="secondary"
                  onClick={() => handleResolveConflict(conflict.task_id, 'ask_user')}
                  disabled={resolvingConflicts.has(conflict.task_id)}
                  className="flex items-center gap-2"
                >
                  <AlertTriangle className="h-4 w-4" />
                  Skip for Now
                </Button>
              </div>
              
              <div className="mt-3 text-sm text-muted-foreground">
                <p><strong>Keep Task Data:</strong> Update calendar event with task information</p>
                <p><strong>Keep Calendar Data:</strong> Update task with calendar event information</p>
                <p><strong>Smart Merge:</strong> Automatically merge data using intelligent rules</p>
                <p><strong>Skip for Now:</strong> Leave conflict unresolved for manual handling later</p>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}

      {/* Bulk Actions */}
      {conflicts.length > 1 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Bulk Actions</CardTitle>
            <CardDescription>
              Apply the same resolution strategy to all conflicts
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => {
                  conflicts.forEach(conflict => 
                    handleResolveConflict(conflict.task_id, 'task_wins')
                  );
                }}
                disabled={resolvingConflicts.size > 0}
              >
                All Tasks Win
              </Button>
              
              <Button
                variant="outline"
                onClick={() => {
                  conflicts.forEach(conflict => 
                    handleResolveConflict(conflict.task_id, 'calendar_wins')
                  );
                }}
                disabled={resolvingConflicts.size > 0}
              >
                All Calendar Wins
              </Button>
              
              <Button
                variant="outline"
                onClick={() => {
                  conflicts.forEach(conflict => 
                    handleResolveConflict(conflict.task_id, 'merge')
                  );
                }}
                disabled={resolvingConflicts.size > 0}
              >
                Smart Merge All
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};