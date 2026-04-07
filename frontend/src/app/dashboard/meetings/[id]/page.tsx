"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiClient } from "@/lib/api-client";
import type { MeetingAnalysis, Meeting } from "@/lib/types";

export default function MeetingDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [meeting, setMeeting] = useState<Meeting | null>(null);
  const [analysis, setAnalysis] = useState<MeetingAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [showTranscript, setShowTranscript] = useState(false);
  const [transcriptInput, setTranscriptInput] = useState("");
  const [uploading, setUploading] = useState(false);

  const meetingId = params.id as string;

  const fetchData = async () => {
    try {
      const [meetingRes, analysisRes] = await Promise.all([
        apiClient.get(`/api/v1/meetings/${meetingId}`),
        apiClient.get(`/api/v1/meetings/${meetingId}/analysis`).catch(() => null),
      ]);
      setMeeting(meetingRes.data);
      if (analysisRes) setAnalysis(analysisRes.data);
    } catch {
      router.push("/dashboard/meetings");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, [meetingId]);

  const handleUploadTranscript = async () => {
    if (!transcriptInput.trim()) return;
    setUploading(true);
    try {
      await apiClient.post(`/api/v1/meetings/${meetingId}/transcript`, {
        transcript: transcriptInput,
      });
      setTranscriptInput("");
      await fetchData();
    } catch {
    } finally {
      setUploading(false);
    }
  };

  const handleReanalyze = async () => {
    try {
      await apiClient.post(`/api/v1/meetings/${meetingId}/analyze`);
      await fetchData();
    } catch {}
  };

  if (loading) {
    return <div className="text-center py-12 text-gray-500">Загрузка...</div>;
  }

  if (!meeting) return null;

  const processingColor: Record<string, string> = {
    pending: "text-gray-500",
    processing: "text-blue-600",
    completed: "text-green-600",
    failed: "text-red-600",
  };

  return (
    <div className="max-w-4xl">
      <button
        onClick={() => router.push("/dashboard/meetings")}
        className="text-sm text-gray-500 hover:text-gray-700 mb-4 inline-block"
      >
        &larr; Все совещания
      </button>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{meeting.title}</h1>
            {meeting.description && (
              <p className="text-gray-600 mt-2">{meeting.description}</p>
            )}
            <div className="flex items-center gap-4 mt-3 text-sm text-gray-500">
              {meeting.scheduled_at && (
                <span>{new Date(meeting.scheduled_at).toLocaleString("ru-RU")}</span>
              )}
              {meeting.duration_minutes && <span>{meeting.duration_minutes} мин.</span>}
              <span className={processingColor[meeting.processing_status] || ""}>
                {meeting.processing_status === "completed" ? "Обработано" :
                 meeting.processing_status === "processing" ? "Обрабатывается..." :
                 meeting.processing_status === "failed" ? "Ошибка обработки" : "Ожидает обработки"}
              </span>
            </div>
          </div>
          <div className="flex gap-2">
            {meeting.transcript && (
              <button
                onClick={handleReanalyze}
                className="px-3 py-1.5 bg-sup-600 text-white rounded-lg text-sm hover:bg-sup-700"
              >
                Повторный анализ
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Upload transcript */}
      {!meeting.transcript && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Загрузить транскрипцию</h2>
          <textarea
            value={transcriptInput}
            onChange={(e) => setTranscriptInput(e.target.value)}
            placeholder="Вставьте текст транскрипции совещания..."
            className="w-full h-40 border border-gray-300 rounded-lg p-3 text-sm resize-y focus:ring-2 focus:ring-sup-500 focus:border-sup-500"
          />
          <button
            onClick={handleUploadTranscript}
            disabled={uploading || !transcriptInput.trim()}
            className="mt-3 px-4 py-2 bg-sup-600 text-white rounded-lg text-sm hover:bg-sup-700 disabled:opacity-50"
          >
            {uploading ? "Загрузка..." : "Загрузить и обработать"}
          </button>
        </div>
      )}

      {/* AI Summary */}
      {analysis?.summary && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">AI-саммари</h2>
          <p className="text-gray-700 whitespace-pre-wrap">{analysis.summary}</p>
        </div>
      )}

      {/* Decisions */}
      {analysis?.decisions && analysis.decisions.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">
            Решения ({analysis.decisions.length})
          </h2>
          <div className="space-y-3">
            {analysis.decisions.map((d) => (
              <div key={d.id} className="border-l-4 border-sup-500 pl-4 py-2">
                <p className="text-sm text-gray-900">{d.content}</p>
                <div className="flex gap-3 mt-1 text-xs text-gray-500">
                  <span>Приоритет: {d.priority}</span>
                  {d.due_date && <span>Срок: {d.due_date}</span>}
                  <span>Статус: {d.status}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tasks */}
      {analysis?.tasks && analysis.tasks.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">
            Задачи ({analysis.tasks.length})
          </h2>
          <div className="space-y-3">
            {analysis.tasks.map((t) => (
              <div key={t.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div>
                  <p className="text-sm font-medium text-gray-900">{t.title}</p>
                  {t.description && <p className="text-xs text-gray-500 mt-1">{t.description}</p>}
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span className={`px-2 py-1 rounded-full ${
                    t.priority === "high" ? "bg-red-100 text-red-700" :
                    t.priority === "low" ? "bg-gray-100 text-gray-700" :
                    "bg-yellow-100 text-yellow-700"
                  }`}>
                    {t.priority}
                  </span>
                  {t.due_date && <span className="text-gray-500">{t.due_date}</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Transcript (collapsible) */}
      {meeting.transcript && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <button
            onClick={() => setShowTranscript(!showTranscript)}
            className="text-lg font-semibold text-gray-900 flex items-center gap-2"
          >
            Транскрипция
            <span className="text-sm font-normal text-gray-400">
              {showTranscript ? "▼" : "▶"}
            </span>
          </button>
          {showTranscript && (
            <pre className="mt-3 text-sm text-gray-700 whitespace-pre-wrap max-h-96 overflow-y-auto">
              {meeting.transcript}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
