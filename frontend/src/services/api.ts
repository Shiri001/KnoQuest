import type { HealthStatus, UploadedFile, EmployeePersona, AdminEmployeeDetail, LoginResponse } from '../types/chat';

const API_BASE_URL = typeof window !== 'undefined' && window.location.hostname
  ? `http://${window.location.hostname}:8000`
  : 'http://localhost:8000';

let onUnauthorizedCallback: (() => void) | null = null;

export function setOnUnauthorizedHandler(cb: () => void) {
  onUnauthorizedCallback = cb;
}

function getStoredToken(): string | null {
  try {
    return sessionStorage.getItem('knoquest_token');
  } catch {
    return null;
  }
}

function setStoredToken(token: string | null) {
  try {
    if (token) {
      sessionStorage.setItem('knoquest_token', token);
    } else {
      sessionStorage.removeItem('knoquest_token');
    }
  } catch {}
}

async function apiFetch(endpoint: string, options: RequestInit = {}): Promise<Response> {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = new Headers(options.headers || {});

  const token = getStoredToken();
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: 'include', // Always send HttpOnly session cookie
  });

  if (response.status === 401) {
    if (onUnauthorizedCallback) {
      onUnauthorizedCallback();
    }
  }

  return response;
}

export async function checkHealth(): Promise<HealthStatus> {
  const res = await apiFetch('/api/health');
  if (!res.ok) {
    throw new Error(`Health check failed: ${res.statusText}`);
  }
  return res.json();
}

export async function loginEmployee(companyId: string, identifier: string, password: string): Promise<LoginResponse> {
  const res = await apiFetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      company_id: companyId.trim().toUpperCase(),
      identifier: identifier.trim(),
      password: password
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Login failed. Please check your credentials.');
  }

  const data: LoginResponse = await res.json();
  if (data.session_token) {
    setStoredToken(data.session_token);
  }
  return data;
}

export async function logoutEmployee(): Promise<void> {
  try {
    await apiFetch('/api/auth/logout', { method: 'POST' });
  } finally {
    setStoredToken(null);
  }
}

export async function fetchCurrentProfile(): Promise<EmployeePersona> {
  const res = await apiFetch('/api/auth/me');
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to load profile: ${res.statusText}`);
  }
  return res.json();
}

export async function sendChatMessage(
  message: string,
  conversationId?: string,
  language: string = 'en',
  sessionFileId?: string
): Promise<{
  answer: string;
  conversation_id: string;
  sources: any[];
  tool_calls: any[];
  mode: string;
  language: string;
  authenticated_user?: any;
}> {
  const res = await apiFetch('/api/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({
      message,
      conversation_id: conversationId || null,
      language,
      session_file_id: sessionFileId || null,
    }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Server error: ${res.statusText}`);
  }

  return res.json();
}

export async function uploadDocument(file: File): Promise<UploadedFile> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await apiFetch('/api/upload', {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Upload failed: ${res.statusText}`);
  }

  return res.json();
}

export async function transcribeAudio(audioBlob: Blob, language: string = 'en'): Promise<{ text: string; language: string }> {
  const formData = new FormData();
  formData.append('audio', audioBlob, 'speech_recording.wav');
  formData.append('language', language);

  const res = await apiFetch('/api/speech/transcribe', {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Transcription failed: ${res.statusText}`);
  }

  return res.json();
}

export async function synthesizeSpeech(text: string, language: string = 'en'): Promise<{
  status: string;
  audio_format: string;
  audio_base64?: string;
  message: string;
}> {
  const res = await apiFetch('/api/speech/synthesize', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, language }),
  });
  if (!res.ok) throw new Error('Failed to synthesize speech');
  return res.json();
}

export async function createTicket(issue: string, priority: string = 'Medium') {
  const res = await apiFetch('/api/tools/ticket', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ issue, priority }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to create ticket');
  }
  return res.json();
}

export async function listTickets(): Promise<{ tickets: any[] }> {
  const res = await apiFetch('/api/tools/tickets');
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to fetch tickets');
  }
  return res.json();
}

export async function searchDirectory(q: string = ''): Promise<{ employees: any[] }> {
  const res = await apiFetch(`/api/tools/directory?q=${encodeURIComponent(q)}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to search employee directory');
  }
  return res.json();
}

// --- Top Team / Admin Console API Functions ---

export async function fetchAdminEmployees(): Promise<EmployeePersona[]> {
  const res = await apiFetch('/api/admin/employees');
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to fetch admin employee directory');
  }
  return res.json();
}

export async function fetchAdminEmployeeDetail(companyId: string, employeeId: string): Promise<AdminEmployeeDetail> {
  const res = await apiFetch(`/api/admin/employees/${companyId}/${employeeId}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to fetch employee details');
  }
  return res.json();
}

export async function updateAdminEmployee(
  companyId: string,
  employeeId: string,
  payload: { role?: string; department?: string; designation?: string; status?: string; password?: string }
): Promise<EmployeePersona> {
  const res = await apiFetch(`/api/admin/employees/${companyId}/${employeeId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to update employee');
  }
  return res.json();
}

export async function setPermissionOverride(
  companyId: string,
  employeeId: string,
  permissionKey: string,
  isGranted: boolean
): Promise<any> {
  const res = await apiFetch(`/api/admin/employees/${companyId}/${employeeId}/permissions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      permission_key: permissionKey,
      is_granted: isGranted
    })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to set permission override');
  }
  return res.json();
}

export async function removePermissionOverride(
  companyId: string,
  employeeId: string,
  permissionKey: string
): Promise<any> {
  const res = await apiFetch(`/api/admin/employees/${companyId}/${employeeId}/permissions/${permissionKey}`, {
    method: 'DELETE'
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to remove permission override');
  }
  return res.json();
}

export async function listCommunications(folder?: string): Promise<{ communications: any[]; count: number }> {
  const url = folder
    ? `/api/tools/communications?folder=${folder}`
    : `/api/tools/communications`;
  const res = await apiFetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to fetch corporate communications');
  }
  return res.json();
}

export async function sendDirectCommunication(
  payload: { recipient: string; subject: string; body: string; channel?: string; draft_id?: string }
) {
  const res = await apiFetch('/api/tools/communications/send', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to send message');
  }
  return res.json();
}

export async function draftDirectCommunication(
  payload: { recipient: string; subject: string; body: string; draft_id?: string }
) {
  const res = await apiFetch('/api/tools/communications/draft', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to save draft');
  }
  return res.json();
}

export async function deleteCommunication(commId: string) {
  const res = await apiFetch(`/api/tools/communications/${commId}`, {
    method: 'DELETE'
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to delete communication');
  }
  return res.json();
}

export async function fetchCalendar() {
  const res = await apiFetch('/api/tools/calendar');
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to fetch calendar');
  }
  return res.json();
}

export async function bookMeeting(payload: { title: string; start_time: string; end_time?: string; attendees?: string; location?: string }) {
  const res = await apiFetch('/api/tools/calendar/book', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to book meeting');
  }
  return res.json();
}

export async function fetchHrProfile() {
  const res = await apiFetch('/api/tools/hr/profile');
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to fetch HR profile');
  }
  return res.json();
}

export async function fetchTeamHr() {
  const res = await apiFetch('/api/tools/hr/team');
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to fetch team HR data');
  }
  return res.json();
}

export async function fetchAllHrPayroll() {
  const res = await apiFetch('/api/tools/hr/payroll');
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to fetch payroll data');
  }
  return res.json();
}

export async function requestLeave(payload: { days: number; leave_type: string; reason?: string }) {
  const res = await apiFetch('/api/tools/hr/leave', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to submit leave request');
  }
  return res.json();
}

export async function fetchPolicies(): Promise<{ policies: any[]; count: number }> {
  const res = await apiFetch('/api/tools/documents/policies');
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to fetch enterprise policies');
  }
  return res.json();
}
