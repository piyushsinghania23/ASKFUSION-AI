import { useEffect, useMemo, useRef, useState } from "react";

import {
  type DocumentItem,
  type TimestampItem,
  API_BASE_URL,
  chat,
  getHealth,
  getSummary,
  getTimestamps,
  listDocuments,
  mediaUrl,
  streamChat,
  uploadFile
} from "./api";

type ChatMessage = {
  id: number;
  role: "user" | "assistant";
  text: string;
  citations: string[];
  timestamps: TimestampItem[];
};

type BackendStatus = "checking" | "connected" | "disconnected";

function formatTime(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  const minutes = Math.floor(total / 60);
  const remain = total % 60;
  return `${minutes}:${remain.toString().padStart(2, "0")}`;
}

export default function App() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string>("");
  const [summary, setSummary] = useState<string>("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState<string>("");
  const [topicQuery, setTopicQuery] = useState<string>("key point");
  const [topicTimestamps, setTopicTimestamps] = useState<TimestampItem[]>([]);
  const [pendingJump, setPendingJump] = useState<TimestampItem | null>(null);
  const [status, setStatus] = useState<string>("Ready");
  const [error, setError] = useState<string>("");
  const [backendStatus, setBackendStatus] = useState<BackendStatus>("checking");
  const [isUploading, setIsUploading] = useState(false);
  const [isAsking, setIsAsking] = useState(false);
  const mediaRef = useRef<HTMLMediaElement | null>(null);

  const selectedDocument = useMemo(
    () => documents.find((doc) => doc.id === selectedDocumentId) ?? null,
    [documents, selectedDocumentId]
  );

  const latestTimestamps = useMemo(() => {
    const assistant = [...messages].reverse().find((msg) => msg.role === "assistant" && msg.timestamps.length > 0);
    return assistant?.timestamps ?? [];
  }, [messages]);

  useEffect(() => {
    void refreshDocuments();
  }, []);

  useEffect(() => {
    let cancelled = false;

    const probeBackend = async () => {
      try {
        const health = await getHealth();
        if (!cancelled) {
          setBackendStatus(health.status === "ok" ? "connected" : "disconnected");
        }
      } catch {
        if (!cancelled) {
          setBackendStatus("disconnected");
        }
      }
    };

    void probeBackend();
    const intervalId = window.setInterval(() => {
      void probeBackend();
    }, 10000);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, []);

  useEffect(() => {
    if (!selectedDocumentId) {
      setSummary("");
      return;
    }
    void (async () => {
      try {
        const summaryText = await getSummary(selectedDocumentId);
        setSummary(summaryText);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load summary.");
      }
    })();
  }, [selectedDocumentId]);

  useEffect(() => {
    if (!pendingJump || !mediaRef.current) {
      return;
    }
    const media = mediaRef.current;
    const playFromTime = () => {
      media.currentTime = pendingJump.start_sec;
      void media.play();
      setPendingJump(null);
    };
    if (media.readyState >= 1) {
      playFromTime();
      return;
    }
    media.addEventListener("loadedmetadata", playFromTime, { once: true });
    return () => media.removeEventListener("loadedmetadata", playFromTime);
  }, [pendingJump, selectedDocumentId]);

  async function refreshDocuments() {
    try {
      const docs = await listDocuments();
      setDocuments(docs);
      if (docs.length > 0 && !docs.find((doc) => doc.id === selectedDocumentId)) {
        setSelectedDocumentId(docs[0].id);
      }
      if (docs.length === 0) {
        setSelectedDocumentId("");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load documents.");
    }
  }

  async function handleUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) {
      return;
    }

    setIsUploading(true);
    setError("");
    setStatus(`Uploading ${file.name}...`);
    try {
      const result = await uploadFile(file);
      setStatus(`Indexed ${result.chunks_indexed} chunks from ${result.document.filename}.`);
      await refreshDocuments();
      setSelectedDocumentId(result.document.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
      setStatus("Upload failed.");
    } finally {
      setIsUploading(false);
    }
  }

  async function handleAsk(useStreaming: boolean) {
    const cleanQuestion = question.trim();
    if (!cleanQuestion || isAsking) {
      return;
    }

    setIsAsking(true);
    setError("");
    setTopicTimestamps([]);
    const selectedIds = selectedDocumentId ? [selectedDocumentId] : [];
    const userMessage: ChatMessage = {
      id: Date.now(),
      role: "user",
      text: cleanQuestion,
      citations: [],
      timestamps: []
    };
    setMessages((prev) => [...prev, userMessage]);
    setQuestion("");

    try {
      if (useStreaming) {
        const assistantId = Date.now() + 1;
        setMessages((prev) => [
          ...prev,
          { id: assistantId, role: "assistant", text: "", citations: [], timestamps: [] }
        ]);
        await streamChat(cleanQuestion, selectedIds, (token) => {
          setMessages((prev) =>
            prev.map((message) =>
              message.id === assistantId ? { ...message, text: `${message.text}${token}` } : message
            )
          );
        });
        setStatus("Streamed response completed.");
      } else {
        const response = await chat(cleanQuestion, selectedIds);
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now() + 1,
            role: "assistant",
            text: response.answer,
            citations: response.citations,
            timestamps: response.timestamps
          }
        ]);
        setStatus("Response generated.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat failed.");
      setStatus("Chat failed.");
    } finally {
      setIsAsking(false);
    }
  }

  async function findTimestampsForTopic() {
    if (!selectedDocumentId) {
      return;
    }
    try {
      const timestamps = await getTimestamps(selectedDocumentId, topicQuery);
      setTopicTimestamps(timestamps);
      setStatus(`Found ${timestamps.length} timestamp matches.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to find timestamps.");
    }
  }

  function jumpToTimestamp(item: TimestampItem) {
    setSelectedDocumentId(item.document_id);
    setPendingJump(item);
  }

  const isMedia = selectedDocument?.file_type === "audio" || selectedDocument?.file_type === "video";

  return (
    <div className="app-shell">
      <header className="hero">
        <p className="eyebrow">ASKFUSION AI</p>
        <h1>Document + Multimedia Intelligence</h1>
        <p className="subtext">
          Upload PDFs, audio, and video. Ask questions, summarize instantly, and jump to exact media timestamps.
        </p>
      </header>

      <main className="layout">
        <section className="panel">
          <h2>1. Upload & Index</h2>
          <label className="upload">
            <input type="file" accept=".pdf,audio/*,video/*" onChange={handleUpload} disabled={isUploading} />
            <span>{isUploading ? "Indexing..." : "Choose PDF / audio / video"}</span>
          </label>
          <p className="status">{status}</p>
          {error ? <p className="error">{error}</p> : null}
          <p className="meta api-meta">
            API: {API_BASE_URL}
            <span className={`backend-badge ${backendStatus}`}>
              {backendStatus === "connected"
                ? "Connected"
                : backendStatus === "disconnected"
                  ? "Disconnected"
                  : "Checking..."}
            </span>
          </p>
        </section>

        <section className="panel">
          <h2>2. Library</h2>
          <div className="document-grid">
            {documents.map((doc) => (
              <button
                key={doc.id}
                type="button"
                className={`document-card ${doc.id === selectedDocumentId ? "active" : ""}`}
                onClick={() => setSelectedDocumentId(doc.id)}
              >
                <strong>{doc.filename}</strong>
                <span>{doc.file_type.toUpperCase()}</span>
              </button>
            ))}
          </div>
          {selectedDocument ? (
            <div className="summary">
              <h3>Summary</h3>
              <p>{summary || selectedDocument.summary || "No summary available yet."}</p>
            </div>
          ) : (
            <p className="meta">Upload at least one file to start.</p>
          )}
        </section>

        <section className="panel">
          <h2>3. Chat</h2>
          <div className="chat-box">
            {messages.map((message) => (
              <article key={message.id} className={`bubble ${message.role}`}>
                <p>{message.text || "..."}</p>
                {message.citations.length > 0 ? (
                  <p className="meta">Sources: {message.citations.join(" | ")}</p>
                ) : null}
                {message.timestamps.length > 0 ? (
                  <div className="timestamp-list">
                    {message.timestamps.map((timestamp, index) => (
                      <button key={`${timestamp.document_id}-${index}`} type="button" onClick={() => jumpToTimestamp(timestamp)}>
                        Play {formatTime(timestamp.start_sec)}-{formatTime(timestamp.end_sec)}
                      </button>
                    ))}
                  </div>
                ) : null}
              </article>
            ))}
          </div>

          <div className="chat-input">
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask about your selected file..."
              rows={3}
            />
            <div className="actions">
              <button type="button" onClick={() => void handleAsk(false)} disabled={isAsking}>
                Ask
              </button>
              <button type="button" onClick={() => void handleAsk(true)} disabled={isAsking}>
                Stream Ask
              </button>
            </div>
          </div>
        </section>

        <section className="panel">
          <h2>4. Timestamp Explorer</h2>
          <div className="topic-row">
            <input value={topicQuery} onChange={(event) => setTopicQuery(event.target.value)} />
            <button type="button" onClick={() => void findTimestampsForTopic()} disabled={!selectedDocumentId}>
              Find
            </button>
          </div>

          <div className="timestamp-list timestamp-list-explorer">
            {[...latestTimestamps, ...topicTimestamps].map((item, index) => (
              <button
                key={`${item.document_id}-${item.start_sec}-${index}`}
                type="button"
                className="timestamp-item"
                onClick={() => jumpToTimestamp(item)}
              >
                <span className="timestamp-range">
                  {formatTime(item.start_sec)}-{formatTime(item.end_sec)}
                </span>
                <span className="timestamp-preview">{item.preview}</span>
              </button>
            ))}
          </div>

          {isMedia && selectedDocument ? (
            <div className="player-wrap">
              {selectedDocument.file_type === "video" ? (
                <video ref={mediaRef as React.RefObject<HTMLVideoElement>} controls src={mediaUrl(selectedDocument.id)} />
              ) : (
                <audio ref={mediaRef as React.RefObject<HTMLAudioElement>} controls src={mediaUrl(selectedDocument.id)} />
              )}
            </div>
          ) : (
            <p className="meta">Select an audio/video file to enable in-app playback.</p>
          )}
        </section>
      </main>
    </div>
  );
}
