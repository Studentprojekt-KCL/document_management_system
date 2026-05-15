// schema for database structure
export interface LogEntry {
  id: number;
  occured: string;
  message: string;
  event_type: string; 
  service: string;
}