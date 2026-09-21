export interface SourceCitation {
  source: string;
  section?: string;
  snippet?: string;
}

export interface ToolCallResult {
  tool_name: string;
  parameters: Record<string, any>;
  result: Record<string, any>;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: SourceCitation[];
  tool_calls?: ToolCallResult[];
  mode?: 'azure_foundry' | 'local_sandbox';
  timestamp: string;
}

export interface HealthStatus {
  status: string;
  service: string;
  version: string;
  mode: string;
  azure_configured: boolean;
  enterprise_docs_loaded: number;
}

export interface LanguageOption {
  code: string;
  name: string;
  nativeName: string;
}

export interface UploadedFile {
  file_id: string;
  filename: string;
  chunks_count: number;
}

export interface EmployeePersona {
  company_id: string;
  employee_id: string;
  full_id: string;
  name: string;
  email: string;
  role: string;
  department: string;
  designation: string;
  status: string;
  extension?: string;
  location?: string;
  effective_permissions?: string[];
}

export interface AdminEmployeeDetail extends EmployeePersona {
  role_permissions: string[];
  overrides: { permission_key: string; is_granted: boolean }[];
}

export interface LoginResponse {
  employee: EmployeePersona;
  session_token: string;
  must_change_password?: boolean;
}
