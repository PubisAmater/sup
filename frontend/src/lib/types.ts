export interface Meeting {
  id: string;
  tenant_id: string;
  title: string;
  description: string | null;
  scheduled_at: string | null;
  duration_minutes: number | null;
  organizer_id: string;
  status: string;
  processing_status: string;
  summary: string | null;
  transcript: string | null;
  notion_page_id: string | null;
  created_at: string;
  decisions?: Decision[];
}

export interface Decision {
  id: string;
  tenant_id: string;
  meeting_id: string;
  content: string;
  decided_by: string;
  assignee_id: string | null;
  due_date: string | null;
  priority: string;
  status: string;
  created_at: string;
}

export interface Task {
  id: string;
  tenant_id: string;
  title: string;
  description: string | null;
  assignee_id: string;
  meeting_id: string | null;
  decision_id: string | null;
  status: string;
  priority: string;
  due_date: string | null;
  notion_page_id: string | null;
  created_at: string;
}

export interface Employee {
  id: string;
  tenant_id: string;
  user_id: string | null;
  position: string;
  department: string;
  hired_at: string | null;
  is_active: boolean;
  created_at: string;
}

export interface DashboardStats {
  employees_count: number;
  meetings_this_week: number;
  tasks_in_progress: number;
  overdue_tasks: number;
}

export interface MeetingAnalysis {
  meeting_id: string;
  processing_status: string;
  processing_error: string | null;
  summary: string | null;
  decisions: Decision[];
  tasks: Task[];
}

export interface WeeklyReport {
  id: string;
  tenant_id: string;
  user_id: string;
  period_start: string;
  period_end: string;
  completed_tasks: string | null;
  metrics_json: string | null;
  requests: string | null;
  status: string;
  submitted_at: string | null;
  created_at: string;
}

export interface MetricSnapshot {
  id: string;
  source: string;
  metric_name: string;
  metric_value: number;
  recorded_at: string;
}

export interface MetricAlert {
  id: string;
  alert_type: string;
  message: string;
  severity: string;
  is_resolved: boolean;
  created_at: string;
}

export interface ScoreEntry {
  id: string;
  user_id: string;
  score_type: string;
  points: number;
  reason: string | null;
  created_at: string;
}

export interface LeaderboardEntry {
  user_id: string;
  first_name: string;
  last_name: string | null;
  total_points: number;
  rank: number;
}
