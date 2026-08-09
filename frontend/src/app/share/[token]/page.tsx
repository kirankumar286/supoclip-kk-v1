"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { AlertCircle, Download, Sparkles, Star, Zap, Check, Share2 } from "lucide-react";

import DynamicVideoPlayer from "@/components/dynamic-video-player";
import { TranscriptPreview } from "@/components/transcript-preview";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatSupportMessage, parseApiError } from "@/lib/api-error";

interface SharedClip {
  id: string;
  filename: string;
  start_time: string;
  end_time: string;
  duration: number;
  text: string;
  relevance_score: number;
  reasoning: string;
  clip_order: number;
  virality_score: number;
  hook_title: string | null;
  social_metadata?: {
    youtube?: { title: string; description: string; hashtags: string[] };
    tiktok?: { title: string; description: string; hashtags: string[] };
    instagram?: { title: string; description: string; hashtags: string[] };
    facebook?: { title: string; description: string; hashtags: string[] };
  } | null;
}

interface SharedTask {
  source_title: string;
  source_type: string;
  status: string;
  clips_count: number;
  created_at: string;
  clips: SharedClip[];
}

function formatDuration(seconds: number) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

interface SocialMetadataPackViewerProps {
  socialMetadata: {
    youtube?: { title: string; description: string; hashtags: string[] };
    tiktok?: { title: string; description: string; hashtags: string[] };
    instagram?: { title: string; description: string; hashtags: string[] };
    facebook?: { title: string; description: string; hashtags: string[] };
  };
}

const SocialMetadataPackViewer: React.FC<SocialMetadataPackViewerProps> = ({ socialMetadata }) => {
  const [activeTab, setActiveTab] = useState<"youtube" | "tiktok" | "instagram" | "facebook">("youtube");
  const [copiedField, setCopiedField] = useState<string | null>(null);

  if (!socialMetadata) return null;

  const currentPack = socialMetadata[activeTab];

  const handleCopy = (text: string, fieldKey: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(`${activeTab}-${fieldKey}`);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const platforms = [
    { id: "youtube", label: "YouTube Shorts", icon: "🔴" },
    { id: "tiktok", label: "TikTok", icon: "🎵" },
    { id: "instagram", label: "Instagram", icon: "📸" },
    { id: "facebook", label: "Facebook", icon: "👥" },
  ] as const;

  return (
    <div className="mt-4 p-4 border border-neutral-100 rounded-xl bg-neutral-50/50 space-y-4">
      <div className="flex items-center justify-between border-b pb-2">
        <h4 className="font-semibold text-sm text-neutral-800 flex items-center gap-1.5">
          <span>🚀</span> Social Upload Pack
        </h4>
        <span className="text-[10px] bg-neutral-200 text-neutral-600 px-2 py-0.5 rounded-full font-medium">AI-Generated</span>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-1.5">
        {platforms.map((p) => (
          <button
            key={p.id}
            onClick={() => setActiveTab(p.id)}
            className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-all flex items-center gap-1.5 ${
              activeTab === p.id
                ? "bg-black text-white shadow-sm"
                : "bg-white text-neutral-600 hover:bg-neutral-100 border border-neutral-200/60"
            }`}
          >
            <span>{p.icon}</span>
            {p.label}
          </button>
        ))}
      </div>

      {/* Content Pack */}
      {currentPack ? (
        <div className="space-y-3 bg-white p-3 rounded-lg border border-neutral-100/80">
          {/* Title */}
          <div className="space-y-1">
            <div className="flex justify-between items-center">
              <span className="text-[11px] font-bold text-neutral-400 uppercase tracking-wider">Optimized Title</span>
              <button
                onClick={() => handleCopy(currentPack.title, "title")}
                className="text-xs text-neutral-500 hover:text-black flex items-center gap-1 transition-colors"
              >
                {copiedField === `${activeTab}-title` ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-green-600" />
                    <span className="text-green-600 font-medium">Copied!</span>
                  </>
                ) : (
                  <>
                    <Share2 className="w-3.5 h-3.5" />
                    <span>Copy</span>
                  </>
                )}
              </button>
            </div>
            <p className="text-sm font-semibold text-neutral-900 leading-relaxed pr-8">
              {currentPack.title || "No title generated"}
            </p>
          </div>

          {/* Description */}
          <div className="space-y-1 border-t pt-2.5">
            <div className="flex justify-between items-center">
              <span className="text-[11px] font-bold text-neutral-400 uppercase tracking-wider">Caption / Description</span>
              <button
                onClick={() => handleCopy(currentPack.description, "description")}
                className="text-xs text-neutral-500 hover:text-black flex items-center gap-1 transition-colors"
              >
                {copiedField === `${activeTab}-description` ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-green-600" />
                    <span className="text-green-600 font-medium">Copied!</span>
                  </>
                ) : (
                  <>
                    <Share2 className="w-3.5 h-3.5" />
                    <span>Copy</span>
                  </>
                )}
              </button>
            </div>
            <p className="text-xs text-neutral-700 whitespace-pre-wrap leading-relaxed pr-8">
              {currentPack.description || "No description generated"}
            </p>
          </div>

          {/* Hashtags */}
          {currentPack.hashtags && currentPack.hashtags.length > 0 && (
            <div className="space-y-1.5 border-t pt-2.5">
              <div className="flex justify-between items-center">
                <span className="text-[11px] font-bold text-neutral-400 uppercase tracking-wider">Recommended Hashtags</span>
                <button
                  onClick={() => handleCopy(currentPack.hashtags.map(h => `#${h}`).join(" "), "hashtags")}
                  className="text-xs text-neutral-500 hover:text-black flex items-center gap-1 transition-colors"
                >
                  {copiedField === `${activeTab}-hashtags` ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-green-600" />
                      <span className="text-green-600 font-medium">Copied!</span>
                    </>
                  ) : (
                    <>
                      <Share2 className="w-3.5 h-3.5" />
                      <span>Copy All</span>
                    </>
                  )}
                </button>
              </div>
              <div className="flex flex-wrap gap-1">
                {currentPack.hashtags.map((h, i) => (
                  <Badge key={i} variant="outline" className="text-[10px] bg-neutral-50 text-neutral-600 font-medium px-2 py-0.5">
                    #{h}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <p className="text-xs text-neutral-400 italic">No post pack generated for this platform.</p>
      )}
    </div>
  );
};

export default function SharedGenerationPage() {
  const params = useParams<{ token: string }>();
  const token = params.token;
  const [task, setTask] = useState<SharedTask | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadSharedTask = useCallback(async () => {
    if (!token) return;

    try {
      const response = await fetch(`/api/share/${encodeURIComponent(token)}`, {
        cache: "no-store",
      });
      if (!response.ok) {
        const parsed = await parseApiError(response, "This share link is unavailable");
        throw new Error(formatSupportMessage(parsed));
      }
      setTask(await response.json());
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "This share link is unavailable");
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void loadSharedTask();
  }, [loadSharedTask]);

  const getClipUrl = (clipId: string) =>
    `/api/share/${encodeURIComponent(token)}/clips/${encodeURIComponent(clipId)}/file`;

  if (isLoading) {
    return (
      <main className="min-h-screen bg-neutral-50 px-4 py-10">
        <div className="mx-auto max-w-6xl space-y-6">
          <Skeleton className="h-9 w-72" />
          <Skeleton className="h-[560px] w-full rounded-xl" />
        </div>
      </main>
    );
  }

  if (error || !task) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-neutral-50 px-4">
        <div className="w-full max-w-lg space-y-5 text-center">
          <Alert variant="destructive" className="text-left">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error || "This share link is unavailable"}</AlertDescription>
          </Alert>
          <Button asChild>
            <Link href="/">Create your own clips</Link>
          </Button>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-neutral-50">
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
          <Link href="/" className="font-[family-name:var(--font-syne)] text-xl font-bold tracking-tight">
            SupoClip
          </Link>
          <Button asChild size="sm">
            <Link href="/">
              <Sparkles className="h-4 w-4" />
              Make your own
            </Link>
          </Button>
        </div>
      </header>

      <div className="mx-auto max-w-6xl px-4 py-8">
        <div className="mb-8">
          <p className="mb-2 text-sm font-medium text-neutral-500">Shared generation</p>
          <h1 className="text-3xl font-bold tracking-tight text-neutral-950">{task.source_title}</h1>
          <div className="mt-3 flex flex-wrap items-center gap-3 text-sm text-neutral-600">
            <Badge variant="outline" className="capitalize">{task.source_type}</Badge>
            <span>{task.clips.length} {task.clips.length === 1 ? "clip" : "clips"}</span>
            <span>{new Date(task.created_at).toLocaleDateString()}</span>
          </div>
        </div>

        <div className="grid gap-6">
          {task.clips.map((clip) => (
            <Card key={clip.id} className="overflow-hidden bg-white py-0">
              <CardContent className="p-0">
                <div className="flex flex-col lg:flex-row">
                  <div className="flex shrink-0 justify-center bg-black p-3 lg:w-[390px]">
                    <DynamicVideoPlayer src={getClipUrl(clip.id)} />
                  </div>
                  <div className="flex flex-1 flex-col p-6">
                    <div className="mb-5 flex items-start justify-between gap-4">
                      <div>
                        <p className="mb-1 text-sm text-neutral-500">Clip {clip.clip_order}</p>
                        <h2 className="text-xl font-semibold text-neutral-950">
                          {clip.hook_title || `Clip ${clip.clip_order}`}
                        </h2>
                        <p className="mt-2 text-sm text-neutral-600">
                          {clip.start_time}–{clip.end_time} · {formatDuration(clip.duration)}
                        </p>
                      </div>
                      <div className="flex shrink-0 gap-2">
                        {clip.virality_score > 0 ? (
                          <Badge>
                            <Zap className="h-3 w-3" />
                            {clip.virality_score}
                          </Badge>
                        ) : null}
                        <Badge variant="secondary">
                          <Star className="h-3 w-3" />
                          {Math.round(clip.relevance_score * 100)}%
                        </Badge>
                      </div>
                    </div>

                    {clip.text ? <TranscriptPreview text={clip.text} clipTitle={clip.hook_title} /> : null}

                    {clip.social_metadata && (
                      <SocialMetadataPackViewer socialMetadata={clip.social_metadata} />
                    )}

                    <div className="mt-auto pt-5">
                      <Button asChild variant="outline">
                        <a href={getClipUrl(clip.id)} download={clip.filename}>
                          <Download className="h-4 w-4" />
                          Download clip
                        </a>
                      </Button>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </main>
  );
}
