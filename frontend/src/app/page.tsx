"use client";

import React, { useState, useEffect } from "react";
import {
  Film,
  Sparkles,
  Bot,
  Mic,
  Video,
  CheckCircle2,
  Clock,
  Play,
  RotateCcw,
  Settings as SettingsIcon,
  Upload,
  AlertCircle,
  ExternalLink,
  ChevronRight,
  Download,
  Copy,
  Check,
  RefreshCw,
  Plus,
  Tv,
  Layers,
  Volume2,
  X,
  Key,
  ShieldCheck,
  Edit3,
  SlidersHorizontal,
  Radio,
  Zap,
  Clapperboard,
  Image as ImageIcon,
  Trash2,
  Eye,
  EyeOff,
} from "lucide-react";

// =============================================================================
// Interfaces & Types
// =============================================================================

export interface Scene {
  scene_number: number;
  narration_es: string;
  visual_prompt_en: string;
  duration_seconds: number;
  media_type?: "video" | "image" | string;
  pexels_search_query?: string | null;
  search_keywords_en?: string | null;
}

export interface ScriptPayload {
  title: string;
  description: string;
  tags: string[];
  scenes: Scene[];
}

export type ShortStatus =
  | "PENDING"
  | "RESEARCHING"
  | "SCRIPTED"
  | "GENERATING_MEDIA"
  | "RENDERING"
  | "READY_FOR_REVIEW"
  | "APPROVED"
  | "PUBLISHED"
  | "FAILED";

export interface ShortItem {
  id: number;
  niche: string;
  topic: string;
  title: string | null;
  script_payload: ScriptPayload | null;
  status: ShortStatus;
  error_message: string | null;
  audio_path: string | null;
  subtitle_path: string | null;
  video_path: string | null;
  youtube_video_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface SystemSettings {
  gemini_api_key_masked: string | null;
  has_gemini_key: boolean;
  gemini_model: string;
  tts_voice: string;
  tts_rate: string;
  youtube_refresh_token_masked: string | null;
  has_youtube_token: boolean;
  pixabay_api_key_masked: string | null;
  has_pixabay_key: boolean;
  auto_schedule_enabled: boolean;
  default_niche: string;
  daily_target_count: number;
  updated_at: string | null;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const BACKEND_URL = API_BASE.replace("/api/v1", "");

const STAGE_STEPS: { key: string; label: string; icon: any }[] = [
  { key: "RESEARCHING", label: "Idea", icon: Bot },
  { key: "SCRIPTED", label: "Guion", icon: Sparkles },
  { key: "GENERATING_MEDIA", label: "Media Híbrida", icon: Mic },
  { key: "RENDERING", label: "Render Pro", icon: Video },
  { key: "READY_FOR_REVIEW", label: "Revisión", icon: Play },
  { key: "PUBLISHED", label: "YouTube", icon: Tv },
];

function getStageIndex(status: ShortStatus): number {
  switch (status) {
    case "PENDING":
      return 0;
    case "RESEARCHING":
      return 0;
    case "SCRIPTED":
      return 1;
    case "GENERATING_MEDIA":
      return 2;
    case "RENDERING":
      return 3;
    case "READY_FOR_REVIEW":
      return 4;
    case "APPROVED":
      return 4;
    case "PUBLISHED":
      return 5;
    case "FAILED":
      return -1;
    default:
      return 0;
  }
}


// =============================================================================
// Interactive Dual-Box API Key Control Component (Casilla 1 + Casilla 2)
// =============================================================================

interface ApiKeyDualControlProps {
  fieldName: "gemini_api_key" | "pixabay_api_key" | "youtube_refresh_token";
  label: string;
  hasKey: boolean;
  maskedValue?: string | null;
  newKeyValue: string;
  onNewKeyChange: (val: string) => void;
  newKeyPlaceholder?: string;
  themeColor?: "cyan" | "indigo" | "red";
  onDeleted?: (updated: SystemSettings) => void;
  notify?: (type: "success" | "error", message: string) => void;
}

function ApiKeyDualControl({
  fieldName,
  label,
  hasKey,
  maskedValue,
  newKeyValue,
  onNewKeyChange,
  newKeyPlaceholder,
  themeColor = "indigo",
  onDeleted,
  notify,
}: ApiKeyDualControlProps) {
  const [isRevealed, setIsRevealed] = useState(false);
  const [revealedValue, setRevealedValue] = useState<string | null>(null);
  const [isLoadingReveal, setIsLoadingReveal] = useState(false);
  const [isCopied, setIsCopied] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Reset revealed state when hasKey or maskedValue changes (e.g. after update or deletion)
  useEffect(() => {
    setIsRevealed(false);
    setRevealedValue(null);
  }, [hasKey, maskedValue]);

  const handleToggleReveal = async () => {
    if (!hasKey) return;

    if (isRevealed) {
      setIsRevealed(false);
      return;
    }

    if (revealedValue) {
      setIsRevealed(true);
      return;
    }

    setIsLoadingReveal(true);
    try {
      const res = await fetch(`${API_BASE}/settings/reveal?field=${fieldName}`);
      if (res.ok) {
        const data = await res.json();
        setRevealedValue(data.value || "");
        setIsRevealed(true);
      } else {
        notify?.("error", `No se pudo revelar la clave vinculada de ${label}.`);
      }
    } catch (err) {
      console.error("Error revealing key:", err);
      notify?.("error", "Error de red al revelar la clave vinculada.");
    } finally {
      setIsLoadingReveal(false);
    }
  };

  const handleCopy = async () => {
    if (!hasKey) return;

    let textToCopy = revealedValue;

    if (textToCopy === null) {
      setIsLoadingReveal(true);
      try {
        const res = await fetch(`${API_BASE}/settings/reveal?field=${fieldName}`);
        if (res.ok) {
          const data = await res.json();
          textToCopy = data.value || "";
          setRevealedValue(textToCopy);
        }
      } catch (err) {
        console.error("Error fetching key for copy:", err);
      } finally {
        setIsLoadingReveal(false);
      }
    }

    if (textToCopy) {
      try {
        await navigator.clipboard.writeText(textToCopy);
        setIsCopied(true);
        notify?.("success", `¡Clave vinculada de ${label} copiada al portapapeles!`);
        setTimeout(() => setIsCopied(false), 2000);
      } catch (err) {
        console.error("Failed to copy:", err);
        notify?.("error", "No se pudo copiar al portapapeles.");
      }
    } else {
      notify?.("error", "No hay una clave activa para copiar.");
    }
  };

  const handleDelete = async () => {
    if (!hasKey) return;

    const confirmed = window.confirm(
      `¿Estás seguro de que deseas eliminar y desvincular la clave actual de ${label}?\n\nEsta acción quitará la clave de la base de datos.`
    );
    if (!confirmed) return;

    setIsDeleting(true);
    try {
      const res = await fetch(`${API_BASE}/settings/key/${fieldName}`, {
        method: "DELETE",
      });
      if (res.ok) {
        const updated: SystemSettings = await res.json();
        setIsRevealed(false);
        setRevealedValue(null);
        onDeleted?.(updated);
        notify?.("success", `Clave vinculada de ${label} eliminada y desvinculada.`);
      } else {
        const err = await res.json().catch(() => ({}));
        notify?.("error", `Error: ${err.detail || "No se pudo eliminar la clave."}`);
      }
    } catch (err) {
      console.error("Error deleting key:", err);
      notify?.("error", "Error de red al eliminar la clave.");
    } finally {
      setIsDeleting(false);
    }
  };

  const borderFocusClass =
    themeColor === "cyan"
      ? "focus:border-cyan-400"
      : themeColor === "red"
      ? "focus:border-red-400"
      : "focus:border-indigo-500";

  return (
    <div className="space-y-3 pt-1">
      {/* Casilla 1: Clave Vinculada Actual */}
      <div className="space-y-1">
        <div className="flex items-center justify-between">
          <label className="text-[10px] uppercase font-bold tracking-wider text-zinc-400 flex items-center gap-1.5">
            <Key className="w-3 h-3 text-cyan-400" />
            <span>Casilla 1 (Clave Vinculada Actual)</span>
          </label>
          {hasKey ? (
            <span className="text-[10px] text-cyan-400 font-mono flex items-center gap-1">
              <ShieldCheck className="w-3 h-3" />
              {isRevealed ? "Texto visible" : "Enmascarada"}
            </span>
          ) : (
            <span className="text-[10px] text-zinc-500 font-mono">
              Sin clave vinculada
            </span>
          )}
        </div>

        <div className="relative flex items-center w-full">
          <input
            type={isRevealed ? "text" : "password"}
            readOnly
            value={
              hasKey
                ? isRevealed
                  ? (revealedValue || "")
                  : (maskedValue || "••••••••")
                : "No hay clave vinculada actualmente en la base de datos"
            }
            className={`w-full bg-zinc-900/90 border rounded-lg pl-3 pr-28 py-2 font-mono text-[11px] select-all cursor-default focus:outline-none transition ${
              hasKey
                ? "border-zinc-800 text-zinc-200"
                : "border-zinc-800/60 text-zinc-500 italic"
            }`}
          />
          <div className="absolute right-1.5 flex items-center gap-1 bg-zinc-900/95 backdrop-blur px-1 py-0.5 rounded-md border border-zinc-800">
            {/* Reveal / Hide Button */}
            <button
              type="button"
              onClick={handleToggleReveal}
              disabled={!hasKey || isLoadingReveal}
              title={isRevealed ? "Ocultar clave vinculada" : "Mostrar clave vinculada en texto plano"}
              className={`p-1 rounded transition ${
                isRevealed
                  ? "text-cyan-400 bg-cyan-950/60"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800"
              } disabled:opacity-30 disabled:pointer-events-none`}
            >
              {isLoadingReveal ? (
                <RefreshCw className="w-3.5 h-3.5 animate-spin text-cyan-400" />
              ) : isRevealed ? (
                <EyeOff className="w-3.5 h-3.5" />
              ) : (
                <Eye className="w-3.5 h-3.5" />
              )}
            </button>

            {/* Copy Button */}
            <button
              type="button"
              onClick={handleCopy}
              disabled={!hasKey || isLoadingReveal}
              title={isCopied ? "¡Copiado!" : "Copiar clave vinculada al portapapeles"}
              className={`p-1 rounded transition flex items-center gap-1 ${
                isCopied
                  ? "text-emerald-400 bg-emerald-950/60"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800"
              } disabled:opacity-30 disabled:pointer-events-none`}
            >
              {isCopied ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-[9px] font-sans font-semibold text-emerald-400 pr-0.5">Copiado</span>
                </>
              ) : (
                <Copy className="w-3.5 h-3.5" />
              )}
            </button>

            {/* Delete Button */}
            <button
              type="button"
              onClick={handleDelete}
              disabled={!hasKey || isDeleting}
              title="Eliminar y desvincular clave de la base de datos"
              className="p-1 rounded text-red-400/70 hover:text-red-400 hover:bg-red-950/50 transition disabled:opacity-30 disabled:pointer-events-none"
            >
              {isDeleting ? (
                <RefreshCw className="w-3.5 h-3.5 animate-spin text-red-400" />
              ) : (
                <Trash2 className="w-3.5 h-3.5" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Casilla 2: Ingresar Nueva Clave */}
      <div className="space-y-1">
        <div className="flex items-center justify-between">
          <label className="text-[10px] uppercase font-bold tracking-wider text-zinc-400 flex items-center gap-1.5">
            <Plus className="w-3 h-3 text-emerald-400" />
            <span>Casilla 2 (Ingresar Nueva Clave)</span>
          </label>
          {newKeyValue.trim() ? (
            <span className="text-[10px] text-emerald-400 font-mono flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              Lista para guardar
            </span>
          ) : (
            <span className="text-[10px] text-zinc-500 font-mono">
              Para vincular o actualizar
            </span>
          )}
        </div>
        <input
          type="password"
          value={newKeyValue}
          onChange={(e) => onNewKeyChange(e.target.value)}
          placeholder={newKeyPlaceholder || "Escribe o pega aquí la nueva clave para actualizar..."}
          className={`w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-white placeholder-zinc-500 font-mono text-[11px] focus:outline-none transition ${borderFocusClass}`}
        />
        <p className="text-[10px] text-zinc-500">
          Al pulsar &quot;Guardar Cambios&quot;, esta clave se vinculará en el backend, la Casilla 1 la reflejará y este campo quedará limpio.
        </p>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  // State
  const [shorts, setShorts] = useState<ShortItem[]>([]);
  const [selectedShortId, setSelectedShortId] = useState<number | null>(null);
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [isSavingSettings, setIsSavingSettings] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [isClearingQueue, setIsClearingQueue] = useState(false);
  const [deletingShortId, setDeletingShortId] = useState<number | null>(null);
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Form Creation State
  const [nicheInput, setNicheInput] = useState("Ciberseguridad y Linux");
  const [topicInput, setTopicInput] = useState("");

  // Settings Form State
  const [settingsGeminiKey, setSettingsGeminiKey] = useState("");
  const [settingsGeminiModel, setSettingsGeminiModel] = useState("gemini-2.5-flash");
  const [customModelMode, setCustomModelMode] = useState(false);
  const [settingsTtsVoice, setSettingsTtsVoice] = useState("es-MX-JorgeNeural");
  const [settingsTtsRate, setSettingsTtsRate] = useState("+10%");
  const [settingsYoutubeToken, setSettingsYoutubeToken] = useState("");
  const [settingsPixabayKey, setSettingsPixabayKey] = useState("");
  const [settingsAutoSchedule, setSettingsAutoSchedule] = useState(false);
  const [settingsDefaultNiche, setSettingsDefaultNiche] = useState("Ciberseguridad y Linux");
  const [settingsDailyTarget, setSettingsDailyTarget] = useState(1);

  // Surgical Scene Editing State (Phase 6 Hybrid)
  const [editingSceneNum, setEditingSceneNum] = useState<number | null>(null);
  const [sceneDraftNarration, setSceneDraftNarration] = useState("");
  const [sceneDraftVisualPrompt, setSceneDraftVisualPrompt] = useState("");
  const [sceneDraftMediaType, setSceneDraftMediaType] = useState<"video" | "image">("image");
  const [sceneDraftPexelsQuery, setSceneDraftPexelsQuery] = useState("");
  const [isRegeneratingScene, setIsRegeneratingScene] = useState(false);

  const selectedShort = shorts.find((s) => s.id === selectedShortId) || shorts[0] || null;

  // Show Toast
  const notify = (type: "success" | "error", message: string) => {
    setNotification({ type, message });
    setTimeout(() => setNotification(null), 4500);
  };

  // Fetch Shorts from API
  const fetchShorts = async () => {
    try {
      const res = await fetch(`${API_BASE}/shorts/`);
      if (res.ok) {
        const data = await res.json();
        setShorts(data.items || []);
        if (selectedShortId === null && data.items && data.items.length > 0) {
          setSelectedShortId(data.items[0].id);
        }
      }
    } catch (err) {
      console.error("Error fetching shorts:", err);
    } finally {
      setIsLoading(false);
    }
  };

  // Fetch Settings from API
  const fetchSettings = async () => {
    try {
      const res = await fetch(`${API_BASE}/settings/`);
      if (res.ok) {
        const data: SystemSettings = await res.json();
        setSettings(data);
        setSettingsGeminiModel(data.gemini_model || "gemini-2.5-flash");
        setSettingsTtsVoice(data.tts_voice || "es-MX-JorgeNeural");
        setSettingsTtsRate(data.tts_rate || "+10%");
        setSettingsAutoSchedule(data.auto_schedule_enabled ?? false);
        setSettingsDefaultNiche(data.default_niche || "Ciberseguridad y Linux");
        setSettingsDailyTarget(data.daily_target_count || 1);
      }
    } catch (err) {
      console.error("Error fetching settings:", err);
    }
  };

  // Polling every 3 seconds for real-time progress
  useEffect(() => {
    fetchShorts();
    fetchSettings();
    const interval = setInterval(fetchShorts, 3000);
    return () => clearInterval(interval);
  }, []);

  // Handle Create Short
  const handleCreateShort = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!nicheInput.trim()) return;

    setIsCreating(true);
    try {
      const res = await fetch(`${API_BASE}/shorts/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          niche: nicheInput.trim(),
          topic: topicInput.trim() || undefined,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Error al crear el Short");
      }

      const created: ShortItem = await res.json();
      setTopicInput("");
      notify("success", `¡Short #${created.id} creado! Pipeline de IA híbrido iniciado.`);
      await fetchShorts();
      setSelectedShortId(created.id);
    } catch (err: any) {
      notify("error", err.message || "Error al conectar con la API");
    } finally {
      setIsCreating(false);
    }
  };

  // Handle Save Settings
  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingSettings(true);
    try {
      const bodyPayload: any = {
        gemini_model: settingsGeminiModel,
        tts_voice: settingsTtsVoice,
        tts_rate: settingsTtsRate,
        auto_schedule_enabled: settingsAutoSchedule,
        default_niche: settingsDefaultNiche,
        daily_target_count: Number(settingsDailyTarget),
      };

      if (settingsGeminiKey.trim()) {
        bodyPayload.gemini_api_key = settingsGeminiKey.trim();
      }
      if (settingsYoutubeToken.trim()) {
        bodyPayload.youtube_refresh_token = settingsYoutubeToken.trim();
      }
      if (settingsPixabayKey.trim()) {
        bodyPayload.pixabay_api_key = settingsPixabayKey.trim();
      }

      const res = await fetch(`${API_BASE}/settings/`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(bodyPayload),
      });

      if (!res.ok) {
        throw new Error("No se pudo actualizar la configuración.");
      }

      const updated = await res.json();
      setSettings(updated);
      setSettingsGeminiKey("");
      setSettingsPixabayKey("");
      setSettingsYoutubeToken("");
      notify("success", "Configuración guardada en vivo. Las credenciales vinculadas han sido actualizadas.");
    } catch (err: any) {
      notify("error", err.message || "Error al guardar configuración");
    } finally {
      setIsSavingSettings(false);
    }
  };

  // Handle YouTube OAuth Connect
  const handleConnectYouTube = async () => {
    try {
      const res = await fetch(`${API_BASE}/youtube/auth-url`);
      const data = await res.json();
      if (data.configured && data.auth_url) {
        window.open(data.auth_url, "_blank");
        notify("success", "Abriendo ventana de autorización de Google OAuth2...");
      } else {
        notify("error", data.message || "Falta configurar credenciales de YouTube en .env");
      }
    } catch (err: any) {
      notify("error", "Error al obtener URL de autorización OAuth2");
    }
  };

  // Handle Approve Short
  const handleApprove = async (id: number) => {
    setIsApproving(true);
    try {
      const res = await fetch(`${API_BASE}/shorts/${id}/approve`, {
        method: "POST",
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Error al aprobar publicación.");
      }
      notify("success", "Short aprobado. Tarea de publicación en YouTube encolada.");
      await fetchShorts();
    } catch (err: any) {
      notify("error", err.message || "Fallo en la aprobación.");
    } finally {
      setIsApproving(false);
    }
  };

  // Handle Retry Short
  const handleRetry = async (id: number) => {
    try {
      const res = await fetch(`${API_BASE}/shorts/${id}/retry`, {
        method: "POST",
      });
      if (!res.ok) throw new Error("Fallo al reintentar Short.");
      notify("success", `Pipeline del Short #${id} re-encolado en Celery.`);
      await fetchShorts();
    } catch (err: any) {
      notify("error", err.message);
    }
  };

  // Handle Clear Stale Queue
  const handleClearStaleQueue = async () => {
    if (
      !confirm(
        "¿Deseas limpiar todos los Shorts pendientes/fallidos de la cola y vaciar Redis? Los videos listos para revisión y publicados se mantendrán intactos."
      )
    ) {
      return;
    }

    setIsClearingQueue(true);
    try {
      const res = await fetch(`${API_BASE}/shorts/queue/clear`, {
        method: "DELETE",
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Error al limpiar la cola");
      }
      const data = await res.json();
      notify("success", `Cola limpiada: ${data.deleted_count} shorts estancados eliminados.`);
      await fetchShorts();
      if (selectedShort && data.deleted_ids?.includes(selectedShort.id)) {
        setSelectedShortId(null);
      }
    } catch (err: any) {
      notify("error", err.message || "Error al limpiar la cola");
    } finally {
      setIsClearingQueue(false);
    }
  };

  // Handle Delete Individual Short
  const handleDeleteShort = async (id: number) => {
    if (!confirm(`¿Eliminar definitivamente el Short #${id} y todos sus archivos multimedia?`)) {
      return;
    }

    setDeletingShortId(id);
    try {
      const res = await fetch(`${API_BASE}/shorts/${id}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Error al eliminar el Short #${id}`);
      }
      notify("success", `Short #${id} y sus archivos han sido eliminados.`);
      if (selectedShortId === id) {
        const remaining = shorts.filter((s) => s.id !== id);
        setSelectedShortId(remaining.length > 0 ? remaining[0].id : null);
      }
      await fetchShorts();
    } catch (err: any) {
      notify("error", err.message || "Error al eliminar");
    } finally {
      setDeletingShortId(null);
    }
  };

  // Handle Surgical Scene Edit
  const handleStartEditScene = (scene: Scene) => {
    setEditingSceneNum(scene.scene_number);
    setSceneDraftNarration(scene.narration_es);
    setSceneDraftVisualPrompt(scene.visual_prompt_en);
    setSceneDraftMediaType(scene.media_type === "video" ? "video" : "image");
    setSceneDraftPexelsQuery(scene.pexels_search_query || "");
  };

  const handleCancelEditScene = () => {
    setEditingSceneNum(null);
    setSceneDraftNarration("");
    setSceneDraftVisualPrompt("");
    setSceneDraftPexelsQuery("");
  };

  const handleRegenerateScene = async (shortId: number, sceneNum: number) => {
    setIsRegeneratingScene(true);
    try {
      const res = await fetch(`${API_BASE}/shorts/${shortId}/scenes/${sceneNum}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          narration_es: sceneDraftNarration,
          visual_prompt_en: sceneDraftVisualPrompt,
          media_type: sceneDraftMediaType,
          pexels_search_query: sceneDraftPexelsQuery,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Error al regenerar escena.");
      }

      const updatedShort: ShortItem = await res.json();
      setShorts((prev) => prev.map((s) => (s.id === updatedShort.id ? updatedShort : s)));
      setEditingSceneNum(null);
      notify("success", `¡Escena #${sceneNum} (${sceneDraftMediaType}) regenerada y Short re-ensamblado en segundos!`);
      await fetchShorts();
    } catch (err: any) {
      notify("error", err.message || "Error al regenerar la escena");
    } finally {
      setIsRegeneratingScene(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#090D16] text-slate-100 flex flex-col font-sans selection:bg-indigo-500/30">
      {/* Toast Notification */}
      {notification && (
        <div
          className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-xl border shadow-2xl backdrop-blur-md flex items-center gap-3 transition-all animate-in slide-in-from-top-2 ${
            notification.type === "success"
              ? "bg-emerald-950/80 border-emerald-500/40 text-emerald-200"
              : "bg-rose-950/80 border-rose-500/40 text-rose-200"
          }`}
        >
          {notification.type === "success" ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          ) : (
            <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
          )}
          <span className="text-xs font-medium">{notification.message}</span>
        </div>
      )}

      {/* Top Header */}
      <header className="border-b border-zinc-800/80 bg-zinc-950/70 backdrop-blur-xl px-6 py-3.5 flex items-center justify-between sticky top-0 z-40">
        <div className="flex items-center space-x-3">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-indigo-600 via-violet-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-indigo-600/30 ring-1 ring-white/20">
            <Film className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-base tracking-tight text-white flex items-center gap-2">
              DASMO OFFICE
              <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                AI Studio Pro v6
              </span>
            </h1>
            <p className="text-[11px] text-zinc-400">
              Motor Híbrido (Pixabay Stock + Flux IA) &middot; Subtítulos Pop-in &middot; Color Grading &middot; SFX
            </p>
          </div>
        </div>

        {/* Live Indicators & Settings Button */}
        <div className="flex items-center gap-3">
          {/* Autopilot Beat Indicator */}
          <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-zinc-900 border border-zinc-800 text-xs">
            <Radio className={`w-3.5 h-3.5 ${settings?.auto_schedule_enabled ? "text-emerald-400 animate-pulse" : "text-zinc-500"}`} />
            <span className="text-zinc-400">Piloto Beat:</span>
            <span className={`font-semibold ${settings?.auto_schedule_enabled ? "text-emerald-300" : "text-zinc-500"}`}>
              {settings?.auto_schedule_enabled ? `${settings.daily_target_count}/día ON` : "OFF"}
            </span>
          </div>

          {/* Pixabay Badge */}
          <div className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-900 border border-zinc-800 text-xs">
            <span className={`w-2 h-2 rounded-full ${settings?.has_pixabay_key ? "bg-cyan-400" : "bg-zinc-600"}`} />
            <span className="text-zinc-400">Pixabay Stock:</span>
            <span className={`font-medium ${settings?.has_pixabay_key ? "text-cyan-300" : "text-zinc-500"}`}>
              {settings?.has_pixabay_key ? "Activo" : "Sin Clave"}
            </span>
          </div>

          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-zinc-900 border border-zinc-800 text-xs">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="text-zinc-400">FastAPI:</span>
            <span className="font-medium text-zinc-200">Online</span>
          </div>

          <button
            onClick={() => setIsSettingsOpen(true)}
            className="flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs transition shadow-md shadow-indigo-600/20 active:scale-95"
          >
            <SettingsIcon className="w-3.5 h-3.5" />
            <span>Ajustes & API Keys</span>
          </button>
        </div>
      </header>

      {/* Main Content Layout */}
      <main className="flex-1 p-6 max-w-[1600px] w-full mx-auto grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Quick Launch & Shorts Monitor (Cols 1 to 5) */}
        <section className="lg:col-span-5 flex flex-col gap-6">
          {/* Quick Creation Card */}
          <div className="bg-zinc-900/60 border border-zinc-800/80 rounded-2xl p-5 backdrop-blur-md shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                  <Sparkles className="w-4 h-4" />
                </div>
                <div>
                  <h2 className="text-sm font-semibold text-white">Crear Nuevo Short</h2>
                  <p className="text-xs text-zinc-400">Generación híbrida ultra-cinematográfica (&lt; 60 segundos)</p>
                </div>
              </div>
            </div>

            <form onSubmit={handleCreateShort} className="space-y-3.5">
              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1">Nicho / Categoría</label>
                <input
                  type="text"
                  value={nicheInput}
                  onChange={(e) => setNicheInput(e.target.value)}
                  placeholder="Ej. Ciberseguridad y Linux, Finanzas, Curiosidades..."
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3.5 py-2 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-indigo-500 transition"
                  required
                />
                {/* Suggestions Tags */}
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {["Ciberseguridad y Linux", "Misterios Históricos", "Finanzas y Cripto", "Inteligencia Artificial"].map(
                    (tag) => (
                      <button
                        key={tag}
                        type="button"
                        onClick={() => setNicheInput(tag)}
                        className="text-[10px] bg-zinc-800/60 hover:bg-zinc-800 text-zinc-300 px-2 py-0.5 rounded-md border border-zinc-700/50 transition"
                      >
                        {tag}
                      </button>
                    )
                  )}
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1">
                  Tema Específico <span className="text-zinc-500 font-normal">(Opcional)</span>
                </label>
                <input
                  type="text"
                  value={topicInput}
                  onChange={(e) => setTopicInput(e.target.value)}
                  placeholder="Dejar vacío para que el Researcher invente un ángulo inédito..."
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3.5 py-2 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-indigo-500 transition"
                />
              </div>

              <button
                type="submit"
                disabled={isCreating}
                className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-indigo-600 via-violet-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 font-medium text-xs text-white shadow-lg shadow-indigo-600/20 flex items-center justify-center gap-2 transition disabled:opacity-50"
              >
                {isCreating ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Orquestando Pipeline Híbrido...</span>
                  </>
                ) : (
                  <>
                    <Zap className="w-3.5 h-3.5 text-amber-300" />
                    <span>Lanzar Short Cinematográfico</span>
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Queue & Pipeline Monitor */}
          <div className="bg-zinc-900/60 border border-zinc-800/80 rounded-2xl p-5 backdrop-blur-md shadow-xl flex-1 flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-indigo-400" />
                <h2 className="text-sm font-semibold text-white">Cola de Procesos</h2>
                <span className="text-[11px] bg-zinc-800 text-zinc-400 px-2 py-0.5 rounded-full font-mono">
                  {shorts.length}
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={handleClearStaleQueue}
                  disabled={isClearingQueue}
                  title="Eliminar Shorts pendientes o fallidos y vaciar cola de Redis"
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-medium bg-rose-500/15 hover:bg-rose-500/25 text-rose-300 border border-rose-500/30 transition disabled:opacity-50"
                >
                  {isClearingQueue ? (
                    <RefreshCw className="w-3 h-3 animate-spin" />
                  ) : (
                    <Trash2 className="w-3 h-3 text-rose-400" />
                  )}
                  <span>Limpiar Cola / Fallidos</span>
                </button>
                <button
                  type="button"
                  onClick={fetchShorts}
                  title="Refrescar lista"
                  className="text-zinc-400 hover:text-white p-1 rounded-md transition"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Shorts Cards List */}
            <div className="space-y-3 overflow-y-auto max-h-[620px] pr-1 scrollbar-thin scrollbar-thumb-zinc-700">
              {shorts.length === 0 ? (
                <div className="text-center py-12 text-zinc-500 text-xs">
                  No hay Shorts generados aún. ¡Crea el primero arriba!
                </div>
              ) : (
                shorts.map((item) => {
                  const isSelected = selectedShort?.id === item.id;
                  const stageIdx = getStageIndex(item.status);

                  return (
                    <div
                      key={item.id}
                      onClick={() => setSelectedShortId(item.id)}
                      className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
                        isSelected
                          ? "bg-indigo-950/20 border-indigo-500/60 shadow-lg shadow-indigo-950/30 ring-1 ring-indigo-500/30"
                          : "bg-zinc-950/40 border-zinc-800/70 hover:border-zinc-700 hover:bg-zinc-900/40"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-[10px] font-mono font-bold text-zinc-400 bg-zinc-800 px-1.5 py-0.5 rounded">
                              #{item.id}
                            </span>
                            <span className="text-xs font-medium text-zinc-300 truncate max-w-[200px]">
                              {item.title || item.topic || item.niche}
                            </span>
                          </div>
                          <span className="text-[10px] text-zinc-500 block truncate max-w-[240px]">
                            {item.niche}
                          </span>
                        </div>

                        {/* Status Badge & Delete Action */}
                        <div className="flex items-center gap-1.5 shrink-0">
                          <StatusBadge status={item.status} />
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteShort(item.id);
                            }}
                            disabled={deletingShortId === item.id}
                            title={`Eliminar Short #${item.id}`}
                            className="p-1 rounded text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 transition disabled:opacity-50"
                          >
                            {deletingShortId === item.id ? (
                              <RefreshCw className="w-3 h-3 animate-spin text-rose-400" />
                            ) : (
                              <Trash2 className="w-3 h-3" />
                            )}
                          </button>
                        </div>
                      </div>

                      {/* Mini Pipeline Progress Steps */}
                      <div className="grid grid-cols-6 gap-1 my-2.5">
                        {STAGE_STEPS.map((s, idx) => {
                          const isDone = item.status === "PUBLISHED" || stageIdx > idx;
                          const isCurrent = stageIdx === idx;
                          const isFailed = item.status === "FAILED";

                          return (
                            <div
                              key={s.key}
                              className={`h-1.5 rounded-full transition-all ${
                                isFailed
                                  ? "bg-rose-500/50"
                                  : isDone
                                  ? "bg-emerald-400"
                                  : isCurrent
                                  ? "bg-indigo-400 animate-pulse"
                                  : "bg-zinc-800"
                              }`}
                              title={s.label}
                            />
                          );
                        })}
                      </div>

                      {/* Card Footer with Details and Actions */}
                      <div className="flex items-center justify-between text-[11px] text-zinc-500 pt-1 border-t border-zinc-800/40">
                        <span>{new Date(item.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                        <div className="flex items-center gap-2">
                          {item.status === "FAILED" && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleRetry(item.id);
                              }}
                              className="flex items-center gap-1 text-rose-400 hover:text-rose-300 bg-rose-500/10 px-2 py-0.5 rounded text-[10px] transition"
                            >
                              <RotateCcw className="w-2.5 h-2.5" />
                              <span>Reintentar</span>
                            </button>
                          )}
                          <ChevronRight className="w-3.5 h-3.5 text-zinc-500" />
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </section>

        {/* Right Column: Review Studio & 9:16 Video Player (Cols 6 to 12) */}
        <section className="lg:col-span-7 flex flex-col gap-6">
          {selectedShort ? (
            <div className="bg-zinc-900/60 border border-zinc-800/80 rounded-2xl p-6 backdrop-blur-md shadow-xl flex-1 flex flex-col">
              {/* Studio Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-5 border-b border-zinc-800/80">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-mono font-bold text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded-full border border-indigo-500/20">
                      Short #{selectedShort.id}
                    </span>
                    <span className="text-xs text-zinc-400">{selectedShort.niche}</span>
                  </div>
                  <h2 className="text-base font-bold text-white tracking-tight">
                    {selectedShort.title || selectedShort.topic || "Generando Guion..."}
                  </h2>
                </div>

                {/* Actions: Approve / Retry / Download */}
                <div className="flex items-center gap-2.5">
                  {selectedShort.video_path && (
                    <a
                      href={`${BACKEND_URL}${selectedShort.video_path}`}
                      download={`short_${selectedShort.id}.mp4`}
                      target="_blank"
                      rel="noreferrer"
                      className="px-3 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium flex items-center gap-1.5 transition"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Descargar MP4</span>
                    </a>
                  )}

                  {selectedShort.status === "READY_FOR_REVIEW" && (
                    <button
                      onClick={() => handleApprove(selectedShort.id)}
                      disabled={isApproving}
                      className="px-4 py-2 rounded-xl bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white font-medium text-xs flex items-center gap-2 shadow-lg shadow-red-600/30 transition active:scale-95 disabled:opacity-50"
                    >
                      {isApproving ? (
                        <>
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                          <span>Subiendo...</span>
                        </>
                      ) : (
                        <>
                          <Upload className="w-3.5 h-3.5" />
                          <span>Aprobar y Subir a YouTube</span>
                        </>
                      )}
                    </button>
                  )}

                  {selectedShort.status === "FAILED" && (
                    <button
                      onClick={() => handleRetry(selectedShort.id)}
                      className="px-4 py-2 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-medium text-xs flex items-center gap-2 shadow-lg shadow-amber-600/30 transition"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      <span>Reintentar Pipeline</span>
                    </button>
                  )}
                </div>
              </div>

              {/* Studio Body: Split Preview 9:16 + Script & Scene Breakdown */}
              <div className="grid grid-cols-1 md:grid-cols-12 gap-6 pt-6 flex-1">
                {/* Vertical 9:16 Video Player Container (5 cols) */}
                <div className="md:col-span-5 flex flex-col items-center">
                  <div className="w-full max-w-[280px] aspect-[9/16] bg-black rounded-2xl overflow-hidden border border-zinc-800 shadow-2xl relative flex items-center justify-center group">
                    {selectedShort.video_path ? (
                      <video
                        key={selectedShort.video_path}
                        src={`${BACKEND_URL}${selectedShort.video_path}`}
                        controls
                        autoPlay
                        loop
                        playsInline
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="flex flex-col items-center justify-center p-6 text-center text-zinc-500">
                        {selectedShort.status === "FAILED" ? (
                          <>
                            <AlertCircle className="w-10 h-10 text-rose-500 mb-2 animate-bounce" />
                            <p className="text-xs text-rose-400 font-medium">Pipeline Fallido</p>
                            <p className="text-[10px] text-zinc-500 mt-1">Revisa el log de error</p>
                          </>
                        ) : (
                          <>
                            <RefreshCw className="w-10 h-10 text-indigo-400 mb-3 animate-spin" />
                            <p className="text-xs text-zinc-300 font-medium">Renderizando Video 9:16 Pro</p>
                            <p className="text-[10px] text-zinc-500 mt-1">
                              Etapa activa: <span className="text-indigo-400">{selectedShort.status}</span>
                            </p>
                          </>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Download MP4 Action under player */}
                  {selectedShort.video_path && (
                    <a
                      href={`${BACKEND_URL}${selectedShort.video_path}`}
                      download={`short_${selectedShort.id}.mp4`}
                      target="_blank"
                      rel="noreferrer"
                      className="w-full max-w-[280px] mt-3 py-2 px-3 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-zinc-100 font-medium text-xs flex items-center justify-center gap-2 border border-zinc-700/60 shadow transition active:scale-95"
                    >
                      <Download className="w-3.5 h-3.5 text-indigo-400" />
                      <span>⬇️ Descargar MP4</span>
                    </a>
                  )}

                  {/* Audio Master Player (Voice + Ambient BGM + Transition SFX) */}
                  {selectedShort.audio_path && (
                    <div className="w-full max-w-[280px] mt-4 p-2.5 rounded-xl bg-zinc-950/80 border border-zinc-800">
                      <div className="flex items-center justify-between mb-1 text-[11px] text-zinc-400">
                        <span className="flex items-center gap-1.5">
                          <Volume2 className="w-3.5 h-3.5 text-indigo-400" />
                          Diseño Sonoro Pro
                        </span>
                        <span className="text-[9px] font-mono text-zinc-500 bg-zinc-900 px-1.5 py-0.5 rounded">Loudnorm + BGM + SFX</span>
                      </div>
                      <audio
                        controls
                        src={`${BACKEND_URL}${selectedShort.audio_path}`}
                        className="w-full h-7 text-xs"
                      />
                    </div>
                  )}
                </div>

                {/* Right Details: Script Breakdown & Metadata (7 cols) */}
                <div className="md:col-span-7 flex flex-col gap-4 overflow-y-auto max-h-[640px] pr-2 scrollbar-thin scrollbar-thumb-zinc-700">
                  {/* YouTube SEO Metadata Card */}
                  {selectedShort.script_payload && (
                    <div className="bg-zinc-950/60 border border-zinc-800/80 rounded-xl p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-semibold text-zinc-300 flex items-center gap-1.5">
                          <Tv className="w-3.5 h-3.5 text-red-500" />
                          Metadatos para YouTube Shorts
                        </span>
                      </div>
                      <p className="text-xs text-zinc-400 mb-2 leading-relaxed">
                        {selectedShort.script_payload.description}
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {selectedShort.script_payload.tags?.map((t, idx) => (
                          <span
                            key={idx}
                            className="text-[10px] font-mono bg-zinc-800/80 text-zinc-300 px-2 py-0.5 rounded-md border border-zinc-700/40"
                          >
                            #{t}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Error Traceback (if failed) */}
                  {selectedShort.status === "FAILED" && selectedShort.error_message && (
                    <div className="bg-rose-950/40 border border-rose-800/50 rounded-xl p-4 text-xs">
                      <h4 className="font-semibold text-rose-300 mb-1 flex items-center gap-1.5">
                        <AlertCircle className="w-4 h-4 text-rose-400" />
                        Detalle del Error
                      </h4>
                      <pre className="text-[10px] text-rose-200/90 whitespace-pre-wrap font-mono max-h-40 overflow-y-auto p-2 bg-black/40 rounded-lg">
                        {selectedShort.error_message}
                      </pre>
                    </div>
                  )}

                  {/* 5-Scene Script Breakdown with Visual Selector & Surgical Edit */}
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-xs font-bold text-zinc-300 uppercase tracking-wider flex items-center gap-1.5">
                        <Film className="w-3.5 h-3.5 text-indigo-400" />
                        Desglose de Escenas &middot; Motor Híbrido
                      </h3>
                      <span className="text-[10px] text-zinc-500">
                        {selectedShort.script_payload?.scenes?.length || 0} escenas (Loop Infinito)
                      </span>
                    </div>

                    {selectedShort.script_payload?.scenes ? (
                      <div className="space-y-3">
                        {selectedShort.script_payload.scenes.map((scene) => {
                          const isEditingThis = editingSceneNum === scene.scene_number;
                          const isVideo = scene.media_type === "video";

                          return (
                            <div
                              key={scene.scene_number}
                              className={`rounded-xl p-3.5 transition border ${
                                isEditingThis
                                  ? "bg-indigo-950/30 border-indigo-500/70 shadow-lg shadow-indigo-950/40 ring-1 ring-indigo-500/40"
                                  : "bg-zinc-950/60 border-zinc-800/70 hover:border-zinc-700"
                              }`}
                            >
                              {/* Scene Header */}
                              <div className="flex items-center justify-between mb-2">
                                <div className="flex items-center gap-2">
                                  <span className="w-5 h-5 rounded-md bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-[10px] text-indigo-400 font-semibold">
                                    {scene.scene_number}
                                  </span>
                                  <span className="text-xs font-semibold text-zinc-200">
                                    Escena #{scene.scene_number}
                                  </span>

                                  {/* Media Type Badge */}
                                  {isVideo ? (
                                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 flex items-center gap-1">
                                      <Clapperboard className="w-3 h-3" /> 🎥 VIDEO B-ROLL (.mp4)
                                    </span>
                                  ) : (
                                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-violet-500/10 text-violet-400 border border-violet-500/30 flex items-center gap-1">
                                      <ImageIcon className="w-3 h-3" /> 🖼️ IMAGEN DINÁMICA (.jpg)
                                    </span>
                                  )}
                                </div>

                                <div className="flex items-center gap-2">
                                  <span className="text-[10px] font-mono text-zinc-500 bg-zinc-900 px-2 py-0.5 rounded border border-zinc-800">
                                    ~{scene.duration_seconds}s
                                  </span>

                                  {!isEditingThis ? (
                                    <button
                                      onClick={() => handleStartEditScene(scene)}
                                      className="flex items-center gap-1 text-[11px] font-medium text-indigo-400 hover:text-indigo-300 bg-indigo-500/10 hover:bg-indigo-500/20 px-2 py-0.5 rounded border border-indigo-500/30 transition"
                                    >
                                      <Edit3 className="w-3 h-3" />
                                      <span>Editar</span>
                                    </button>
                                  ) : null}
                                </div>
                              </div>

                              {/* Normal View or Interactive Surgical Edit Form */}
                              {isEditingThis ? (
                                <div className="space-y-3 mt-3 pt-3 border-t border-zinc-800">
                                  {/* Media Type Toggle Selector */}
                                  <div>
                                    <label className="text-[10px] uppercase font-bold text-zinc-400 block mb-1.5">
                                      Tipo de Recurso Visual:
                                    </label>
                                    <div className="grid grid-cols-2 gap-2">
                                      <button
                                        type="button"
                                        onClick={() => setSceneDraftMediaType("video")}
                                        className={`py-1.5 px-3 rounded-lg text-xs font-medium flex items-center justify-center gap-1.5 border transition ${
                                          sceneDraftMediaType === "video"
                                            ? "bg-cyan-950/60 border-cyan-500 text-cyan-200 shadow-md shadow-cyan-950/40"
                                            : "bg-zinc-900 border-zinc-800 text-zinc-400 hover:text-white"
                                        }`}
                                      >
                                        <Clapperboard className="w-3.5 h-3.5" />
                                        <span>🎥 Video B-Roll (.mp4)</span>
                                      </button>
                                      <button
                                        type="button"
                                        onClick={() => setSceneDraftMediaType("image")}
                                        className={`py-1.5 px-3 rounded-lg text-xs font-medium flex items-center justify-center gap-1.5 border transition ${
                                          sceneDraftMediaType === "image"
                                            ? "bg-violet-950/60 border-violet-500 text-violet-200 shadow-md shadow-violet-950/40"
                                            : "bg-zinc-900 border-zinc-800 text-zinc-400 hover:text-white"
                                        }`}
                                      >
                                        <ImageIcon className="w-3.5 h-3.5" />
                                        <span>🖼️ Imagen Dinámica (.jpg)</span>
                                      </button>
                                    </div>
                                  </div>

                                  {/* If Video: Pexels Search Query */}
                                  {sceneDraftMediaType === "video" && (
                                    <div>
                                      <label className="text-[10px] uppercase font-bold text-cyan-400 block mb-1">
                                        Búsqueda B-Roll en Pixabay (Inglés, 2-4 palabras):
                                      </label>
                                      <input
                                        type="text"
                                        value={sceneDraftPexelsQuery}
                                        onChange={(e) => setSceneDraftPexelsQuery(e.target.value)}
                                        className="w-full bg-zinc-900 border border-cyan-700/60 rounded-lg p-2 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-cyan-400 transition"
                                        placeholder="ej. hacker dark room, server rack lights, cybersecurity matrix..."
                                      />
                                    </div>
                                  )}

                                  {/* Edit Visual Prompt */}
                                  <div>
                                    <label className="text-[10px] uppercase font-bold text-zinc-400 block mb-1">
                                      Prompt Visual 9:16 (Inglés para Flux / Fallback):
                                    </label>
                                    <textarea
                                      rows={2}
                                      value={sceneDraftVisualPrompt}
                                      onChange={(e) => setSceneDraftVisualPrompt(e.target.value)}
                                      className="w-full bg-zinc-900 border border-zinc-700 rounded-lg p-2 text-xs text-white font-mono placeholder-zinc-500 focus:outline-none focus:border-indigo-500 transition"
                                      placeholder="Detailed prompt for 9:16 vertical visual..."
                                    />
                                  </div>

                                  {/* Edit Narration */}
                                  <div>
                                    <label className="text-[10px] uppercase font-bold text-zinc-400 block mb-1">
                                      Editar Locución (Español):
                                    </label>
                                    <textarea
                                      rows={2}
                                      value={sceneDraftNarration}
                                      onChange={(e) => setSceneDraftNarration(e.target.value)}
                                      className="w-full bg-zinc-900 border border-zinc-700 rounded-lg p-2 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-indigo-500 transition"
                                      placeholder="Escribe la nueva locución para esta escena..."
                                    />
                                  </div>

                                  {/* Surgical Actions */}
                                  <div className="flex items-center justify-end gap-2 pt-1">
                                    <button
                                      type="button"
                                      onClick={handleCancelEditScene}
                                      disabled={isRegeneratingScene}
                                      className="px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-medium transition"
                                    >
                                      Cancelar
                                    </button>
                                    <button
                                      type="button"
                                      disabled={isRegeneratingScene}
                                      onClick={() => handleRegenerateScene(selectedShort.id, scene.scene_number)}
                                      className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium flex items-center gap-1.5 shadow-md shadow-indigo-600/30 transition disabled:opacity-50"
                                    >
                                      {isRegeneratingScene ? (
                                        <>
                                          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                                          <span>Regenerando Escena Híbrida...</span>
                                        </>
                                      ) : (
                                        <>
                                          <Zap className="w-3.5 h-3.5 text-amber-300" />
                                          <span>Regenerar Escena ({sceneDraftMediaType.toUpperCase()})</span>
                                        </>
                                      )}
                                    </button>
                                  </div>
                                </div>
                              ) : (
                                <>
                                  {/* Narration */}
                                  <div className="mb-2.5">
                                    <span className="text-[10px] uppercase font-bold text-zinc-500 block mb-0.5">
                                      Locución (Español):
                                    </span>
                                    <p className="text-xs text-zinc-200 leading-relaxed font-sans bg-zinc-900/40 p-2 rounded-lg border border-zinc-800/40">
                                      "{scene.narration_es}"
                                    </p>
                                  </div>

                                  {/* Visual Info */}
                                  <div>
                                    <div className="flex items-center justify-between mb-0.5">
                                      <span className="text-[10px] uppercase font-bold text-zinc-500 block">
                                        {isVideo ? "B-Roll Query (Pixabay):" : "Prompt Visual 9:16 (Flux):"}
                                      </span>
                                      {scene.pexels_search_query && (
                                        <span className="text-[9px] font-mono text-cyan-400 bg-cyan-950/40 px-1.5 py-0.2 rounded border border-cyan-800/40">
                                          Pixabay: {scene.pexels_search_query}
                                        </span>
                                      )}
                                    </div>
                                    <p className="text-[11px] text-zinc-400 font-mono italic leading-relaxed bg-black/30 p-2 rounded-lg border border-zinc-900">
                                      {scene.visual_prompt_en}
                                    </p>
                                  </div>
                                </>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <div className="text-xs text-zinc-500 p-6 text-center bg-zinc-950/40 rounded-xl border border-zinc-800/50">
                        {selectedShort.status === "PENDING" || selectedShort.status === "RESEARCHING"
                          ? "Los agentes de Gemini están investigando y redactando el guion..."
                          : "No hay guion disponible para este Short."}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-zinc-900/60 border border-zinc-800/80 rounded-2xl p-12 text-center text-zinc-500 text-xs">
              Selecciona un Short de la lista para ver su estudio de revisión y video 9:16.
            </div>
          )}
        </section>
      </main>

      {/* Settings Modal */}
      {isSettingsOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in">
          <div className="bg-zinc-900 border border-zinc-800 w-full max-w-xl rounded-2xl p-6 shadow-2xl relative max-h-[90vh] overflow-y-auto scrollbar-thin scrollbar-thumb-zinc-700">
            <div className="flex items-center justify-between pb-4 border-b border-zinc-800 mb-5">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                  <Key className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">Configuración del Sistema Pro</h3>
                  <p className="text-xs text-zinc-400">Actualiza claves, modelos y piloto automático en caliente</p>
                </div>
              </div>
              <button
                onClick={() => setIsSettingsOpen(false)}
                className="text-zinc-500 hover:text-white p-1 rounded-lg transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveSettings} className="space-y-4 text-xs">
              {/* SECTION: PILOTO AUTOMATICO (CELERY BEAT) */}
              <div className="p-4 rounded-xl bg-indigo-950/20 border border-indigo-500/30 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Radio className="w-4 h-4 text-indigo-400" />
                    <div>
                      <h4 className="font-semibold text-white text-xs">Piloto Automático (Celery Beat)</h4>
                      <p className="text-[11px] text-zinc-400">Crea y encola Shorts diariamente sin intervención manual</p>
                    </div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settingsAutoSchedule}
                      onChange={(e) => setSettingsAutoSchedule(e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-9 h-5 bg-zinc-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-zinc-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-indigo-600"></div>
                  </label>
                </div>

                {settingsAutoSchedule && (
                  <div className="grid grid-cols-2 gap-3 pt-2 border-t border-indigo-500/20">
                    <div>
                      <label className="block text-[11px] font-medium text-zinc-300 mb-1">
                        Nicho por Defecto
                      </label>
                      <input
                        type="text"
                        value={settingsDefaultNiche}
                        onChange={(e) => setSettingsDefaultNiche(e.target.value)}
                        placeholder="Ej. Ciberseguridad y Linux"
                        className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-medium text-zinc-300 mb-1">
                        Meta Diaria de Shorts
                      </label>
                      <select
                        value={settingsDailyTarget}
                        onChange={(e) => setSettingsDailyTarget(Number(e.target.value))}
                        className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                      >
                        <option value={1}>1 Short por día</option>
                        <option value={2}>2 Shorts por día</option>
                        <option value={3}>3 Shorts por día</option>
                        <option value={5}>5 Shorts por día</option>
                      </select>
                    </div>
                  </div>
                )}
              </div>

              {/* SECTION: PIXABAY API KEY (VIDEOS E IMÁGENES) */}
              <div className="p-3.5 rounded-xl bg-zinc-950 border border-zinc-800 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Clapperboard className="w-4 h-4 text-cyan-400" />
                    <div>
                      <label className="font-semibold text-zinc-200 block text-xs">Pixabay API Key (Videos e Imágenes)</label>
                      <span className="text-[10px] text-zinc-400">Descarga clips de video B-Roll y fotografías stock en alta definición</span>
                    </div>
                  </div>
                  {settings?.has_pixabay_key ? (
                    <span className="text-[10px] text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded-full border border-cyan-500/20 flex items-center gap-1 font-mono">
                      <ShieldCheck className="w-3 h-3" /> Configurado: {settings.pixabay_api_key_masked || "••••••••"}
                    </span>
                  ) : (
                    <span className="text-[10px] text-zinc-500 bg-zinc-800/80 px-2 py-0.5 rounded-full border border-zinc-700/40">No configurado</span>
                  )}
                </div>
                <div className="flex items-center justify-end pt-0.5">
                  <a
                    href="https://pixabay.com/api/docs/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-blue-400 hover:text-blue-300 inline-flex items-center gap-1 transition"
                  >
                    <span>Obtener clave gratuita en Pixabay API</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
                <ApiKeyDualControl
                  fieldName="pixabay_api_key"
                  label="Pixabay API Key"
                  hasKey={Boolean(settings?.has_pixabay_key)}
                  maskedValue={settings?.pixabay_api_key_masked}
                  newKeyValue={settingsPixabayKey}
                  onNewKeyChange={setSettingsPixabayKey}
                  newKeyPlaceholder="Pega aquí tu nueva PIXABAY_API_KEY para vincular..."
                  themeColor="cyan"
                  onDeleted={(updated) => setSettings(updated)}
                  notify={notify}
                />
              </div>

              {/* Gemini API Key */}
              <div className="p-3.5 rounded-xl bg-zinc-950 border border-zinc-800 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-indigo-400" />
                    <div>
                      <label className="font-semibold text-zinc-200 block text-xs">Google Gemini API Key</label>
                      <span className="text-[10px] text-zinc-400">Guionización cinematográfica y generación de prompts visuales</span>
                    </div>
                  </div>
                  {settings?.has_gemini_key ? (
                    <span className="text-[10px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20 flex items-center gap-1 font-mono">
                      <ShieldCheck className="w-3 h-3" /> Vinculado: {settings.gemini_api_key_masked || "••••••••"}
                    </span>
                  ) : (
                    <span className="text-[10px] text-zinc-500 bg-zinc-800/80 px-2 py-0.5 rounded-full border border-zinc-700/40">No configurado</span>
                  )}
                </div>
                <div className="flex items-center justify-end pt-0.5">
                  <a
                    href="https://aistudio.google.com/app/apikey"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-blue-400 hover:text-blue-300 inline-flex items-center gap-1 transition"
                  >
                    <span>Obtener clave en Google AI Studio</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
                <ApiKeyDualControl
                  fieldName="gemini_api_key"
                  label="Google Gemini API Key"
                  hasKey={Boolean(settings?.has_gemini_key)}
                  maskedValue={settings?.gemini_api_key_masked}
                  newKeyValue={settingsGeminiKey}
                  onNewKeyChange={setSettingsGeminiKey}
                  newKeyPlaceholder="Pega aquí tu nueva GEMINI_API_KEY para vincular..."
                  themeColor="indigo"
                  onDeleted={(updated) => setSettings(updated)}
                  notify={notify}
                />
              </div>

              {/* Gemini Model Selection */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="font-semibold text-zinc-300">Modelo Gemini</label>
                  <button
                    type="button"
                    onClick={() => setCustomModelMode(!customModelMode)}
                    className="text-[10px] text-indigo-400 hover:underline"
                  >
                    {customModelMode ? "Seleccionar de la lista" : "Escribir modelo personalizado"}
                  </button>
                </div>

                {customModelMode ? (
                  <input
                    type="text"
                    value={settingsGeminiModel}
                    onChange={(e) => setSettingsGeminiModel(e.target.value)}
                    placeholder="ej. gemini-3-flash-preview"
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3.5 py-2 text-white font-mono focus:outline-none focus:border-indigo-500"
                    required
                  />
                ) : (
                  <select
                    value={settingsGeminiModel}
                    onChange={(e) => setSettingsGeminiModel(e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3.5 py-2 text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="gemini-2.5-flash">gemini-2.5-flash (Predeterminado - Ultra Rápido)</option>
                    <option value="gemini-3-flash-preview">gemini-3-flash-preview (Nueva Generación)</option>
                    <option value="gemini-1.5-flash">gemini-1.5-flash (Estable)</option>
                    <option value="gemini-1.5-pro">gemini-1.5-pro (Máxima Capacidad Creativa)</option>
                  </select>
                )}
              </div>

              {/* Edge TTS Voice */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold text-zinc-300 block mb-1">Voz del Narrador (TTS)</label>
                  <select
                    value={settingsTtsVoice}
                    onChange={(e) => setSettingsTtsVoice(e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3.5 py-2 text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="es-MX-JorgeNeural">es-MX-JorgeNeural (México - Profundo)</option>
                    <option value="es-PE-CamilaNeural">es-PE-CamilaNeural (Perú - Femenino)</option>
                    <option value="es-ES-AlvaroNeural">es-ES-AlvaroNeural (España - Dinámico)</option>
                    <option value="es-US-AlonsoNeural">es-US-AlonsoNeural (EEUU - Enérgico)</option>
                    <option value="es-AR-TomasNeural">es-AR-TomasNeural (Argentina)</option>
                    <option value="es-CO-GonzaloNeural">es-CO-GonzaloNeural (Colombia)</option>
                  </select>
                </div>

                <div>
                  <label className="font-semibold text-zinc-300 block mb-1">Velocidad de Voz</label>
                  <select
                    value={settingsTtsRate}
                    onChange={(e) => setSettingsTtsRate(e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3.5 py-2 text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="+0%">Normal (+0%)</option>
                    <option value="+10%">Rápido Dinámico (+10%)</option>
                    <option value="+15%">Alta Retención (+15%)</option>
                  </select>
                </div>
              </div>

              {/* SECTION: YOUTUBE OAUTH2 & TOKEN */}
              <div className="p-3.5 rounded-xl bg-zinc-950 border border-zinc-800 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Tv className="w-4 h-4 text-red-500" />
                    <span className="font-semibold text-zinc-200">YouTube Data API v3</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <a
                      href="https://console.cloud.google.com/apis/credentials"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-blue-400 hover:text-blue-300 inline-flex items-center gap-1 transition"
                    >
                      <span>Crear credenciales en Google Cloud Console</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                    {settings?.has_youtube_token ? (
                      <span className="text-[10px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20 flex items-center gap-1 font-mono">
                        <Check className="w-3 h-3" /> Conectado: {settings.youtube_refresh_token_masked || "••••••••"}
                      </span>
                    ) : (
                      <span className="text-[10px] text-zinc-500 bg-zinc-800/80 px-2 py-0.5 rounded-full border border-zinc-700/40">
                        No configurado
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex flex-col sm:flex-row gap-2">
                  <button
                    type="button"
                    onClick={handleConnectYouTube}
                    className="flex-1 py-2 px-3 rounded-lg bg-red-600 hover:bg-red-500 text-white font-medium text-xs flex items-center justify-center gap-2 shadow transition"
                  >
                    <Tv className="w-3.5 h-3.5" />
                    <span>Conectar Canal de YouTube (OAuth2)</span>
                  </button>
                </div>

                <div className="pt-1">
                  <ApiKeyDualControl
                    fieldName="youtube_refresh_token"
                    label="YouTube Refresh Token"
                    hasKey={Boolean(settings?.has_youtube_token)}
                    maskedValue={settings?.youtube_refresh_token_masked}
                    newKeyValue={settingsYoutubeToken}
                    onNewKeyChange={setSettingsYoutubeToken}
                    newKeyPlaceholder="Pega aquí el nuevo refresh_token para vincular..."
                    themeColor="red"
                    onDeleted={(updated) => setSettings(updated)}
                    notify={notify}
                  />
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-end gap-3 pt-3 border-t border-zinc-800">
                <button
                  type="button"
                  onClick={() => setIsSettingsOpen(false)}
                  className="px-4 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-zinc-300 font-medium transition"
                >
                  Cerrar
                </button>
                <button
                  type="submit"
                  disabled={isSavingSettings}
                  className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium shadow-lg shadow-indigo-600/30 flex items-center gap-2 transition disabled:opacity-50"
                >
                  {isSavingSettings ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Guardando...</span>
                    </>
                  ) : (
                    <span>Guardar Cambios</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Helper Component: Status Badge
// =============================================================================
function StatusBadge({ status }: { status: ShortStatus }) {
  switch (status) {
    case "PENDING":
      return (
        <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400 border border-zinc-700">
          En Cola
        </span>
      );
    case "RESEARCHING":
      return (
        <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 animate-pulse">
          Investigando
        </span>
      );
    case "SCRIPTED":
      return (
        <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-violet-500/10 text-violet-400 border border-violet-500/20">
          Guion Listo
        </span>
      );
    case "GENERATING_MEDIA":
      return (
        <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse">
          Media Híbrida
        </span>
      );
    case "RENDERING":
      return (
        <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-orange-500/10 text-orange-400 border border-orange-500/20 animate-pulse">
          Render Pro
        </span>
      );
    case "READY_FOR_REVIEW":
      return (
        <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 shadow-sm shadow-emerald-500/20 flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span>
          Listo para Revisión
        </span>
      );
    case "APPROVED":
      return (
        <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
          Aprobado
        </span>
      );
    case "PUBLISHED":
      return (
        <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
          <Check className="w-3 h-3 text-emerald-400" />
          Publicado
        </span>
      );
    case "FAILED":
      return (
        <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/30 flex items-center gap-1">
          <AlertCircle className="w-2.5 h-2.5 text-rose-400" />
          Fallido
        </span>
      );
    default:
      return null;
  }
}
