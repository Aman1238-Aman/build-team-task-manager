import type {
  AuthResponse,
  Dashboard,
  Project,
  ProjectRole,
  Role,
  Task,
  TaskPriority,
  TaskStatus,
  User,
} from "./types";

// ✅ Production-safe API base
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL;

if (!API_BASE) {
  throw new Error("❌ NEXT_PUBLIC_API_BASE_URL is not defined");
}

type ApiOptions = {
  token?: string;
  method?: string;
  body?: unknown;
};

async function request<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: options.method ?? "GET",
    headers: {
      "Content-Type": "application/json",
      ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}),
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
    cache: "no-store",
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(typeof payload.detail === "string" ? payload.detail : "Request failed");
  }

  return response.json() as Promise<T>;
}

export const api = {
  signup(payload: { name: string; email: string; password: string; role: Role }) {
    return request<AuthResponse>("/auth/signup", {
      method: "POST",
      body: payload,
    });
  },

  login(payload: { email: string; password: string }) {
    return request<AuthResponse>("/auth/login", {
      method: "POST",
      body: payload,
    });
  },

  me(token: string) {
    return request<User>("/auth/me", { token });
  },

  users(token: string) {
    return request<User[]>("/users", { token });
  },

  dashboard(token: string) {
    return request<Dashboard>("/dashboard", { token });
  },

  projects(token: string) {
    return request<Project[]>("/projects", { token });
  },

  tasks(token: string) {
    return request<Task[]>("/tasks", { token });
  },

  createProject(token: string, payload: { name: string; description: string }) {
    return request<Project>("/projects", {
      token,
      method: "POST",
      body: payload,
    });
  },

  addMember(token: string, projectId: number, payload: { email: string; role: ProjectRole }) {
    return request(`/projects/${projectId}/members`, {
      token,
      method: "POST",
      body: payload,
    });
  },

  createTask(
    token: string,
    projectId: number,
    payload: {
      title: string;
      description: string;
      priority: TaskPriority;
      due_date: string | null;
      assignee_id: number | null;
    }
  ) {
    return request<Task>(`/projects/${projectId}/tasks`, {
      token,
      method: "POST",
      body: payload,
    });
  },

  updateTask(
    token: string,
    taskId: number,
    payload: Partial<{
      title: string;
      description: string;
      status: TaskStatus;
      priority: TaskPriority;
      due_date: string | null;
      assignee_id: number | null;
    }>
  ) {
    return request<Task>(`/tasks/${taskId}`, {
      token,
      method: "PATCH",
      body: payload,
    });
  },
};
