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
