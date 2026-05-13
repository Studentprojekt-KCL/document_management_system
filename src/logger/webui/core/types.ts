// schema for database structure
interface LogEntry {
  id: number;
  occured: string;
  message: string;
  event_type: string; 
  service: string;
}