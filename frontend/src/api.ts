export type DocumentItem = {
  id: string;
  filename: string;
  file_type: string;
  summary: string;
  created_at: string;
};

export type TimestampItem = {
  document_id: string;
  start_sec: number;
  end_sec: number;
  preview: string;
};

export type ChatResponse = {
  answer: string;
  citations: string[];
  timestamps: TimestampItem[];
};

export type HealthResponse = {
  status: string;
  service: string;
};

const envBase = import.meta.env.VITE_API_BASE_URL;

function defaultApiBaseUrl(): string {
  if (typeof window === "undefined") {
    return "http://localhost:8000";
  }
  const protocol = window.location.protocol === "https:" ? "https" : "http";
  const rawHost = window.location.hostname || "localhost";
  const host = rawHost.includes(":") ? `[${rawHost}]` : rawHost;
  return `${protocol}://${host}:8000`;
}

export const API_BASE_URL =
  typeof envBase === "string" && envBase.trim() ? envBase.replace(/\/$/, "") : defaultApiBaseUrl();

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export async function uploadFile(file: File): Promise<{ document: DocumentItem; chunks_indexed: number }> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_BASE_URL}/api/upload`, {
    method: "POST",
    body: formData
  });
  return handleResponse(response);
}

export async function listDocuments(): Promise<DocumentItem[]> {
  const response = await fetch(`${API_BASE_URL}/api/documents`);
  return handleResponse(response);
}

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`);
  return handleResponse(response);
}

export async function getSummary(documentId: string): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/api/documents/${documentId}/summary`);
  const payload = await handleResponse<{ summary: string }>(response);
  return payload.summary;
}

export async function getTimestamps(documentId: string, topic: string): Promise<TimestampItem[]> {
  const query = new URLSearchParams({ topic });
  const response = await fetch(`${API_BASE_URL}/api/documents/${documentId}/timestamps?${query.toString()}`);
  return handleResponse(response);
}

export async function chat(question: string, documentIds: string[], topK = 4): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, document_ids: documentIds, top_k: topK })
  });
  return handleResponse(response);
}

export async function streamChat(
  question: string,
  documentIds: string[],
  onToken: (token: string) => void,
  topK = 4
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, document_ids: documentIds, top_k: topK })
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  if (!response.body) {
    throw new Error("Streaming is not supported by this browser.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";

    for (const block of blocks) {
      for (const line of block.split("\n")) {
        if (!line.startsWith("data:")) {
          continue;
        }
        const data = line.slice(5).trim();
        if (data === "[DONE]") {
          return;
        }
        onToken(data);
      }
    }
  }
}

export function mediaUrl(documentId: string): string {
  return `${API_BASE_URL}/api/documents/${documentId}/media`;
}
