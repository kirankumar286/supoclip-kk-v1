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
  socialMetadata: any;
}

const SocialMetadataPackViewer: React.FC<SocialMetadataPackViewerProps> = ({ socialMetadata }) => {
  const [activeTab, setActiveTab] = useState<"instagram" | "tiktok" | "youtube" | "facebook" | "snapchat" | "pinterest" | "x_threads">("instagram");
  const [copiedField, setCopiedField] = useState<string | null>(null);

  if (!socialMetadata) return null;

  const currentPack = socialMetadata[activeTab];

  const handleCopy = (text: string, fieldKey: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(`${activeTab}-${fieldKey}`);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const platforms = [
    { id: "instagram", label: "Instagram Reels", icon: "📸" },
    { id: "tiktok", label: "TikTok", icon: "🎵" },
    { id: "youtube", label: "YouTube Shorts", icon: "🔴" },
    { id: "facebook", label: "Facebook Reels", icon: "👥" },
    { id: "snapchat", label: "Snapchat", icon: "👻" },
    { id: "pinterest", label: "Pinterest", icon: "📌" },
    { id: "x_threads", label: "X / Threads", icon: "💬" },
  ] as const;

  const handleDownload = () => {
    let output = `==================================================\n`;
    output += `SUPO CLIP SOCIAL MEDIA METADATA PACK\n`;
    output += `==================================================\n\n`;

    const formatSection = (title: string, data: any) => {
      if (!data) return "";
      let sec = `--------------------------------------------------\n`;
      sec += `${title.toUpperCase()}\n`;
      sec += `--------------------------------------------------\n`;

      if (data.hook_options && data.hook_options.length > 0) {
        sec += `Hook/Title Options:\n`;
        data.hook_options.forEach((opt: string, idx: number) => {
          sec += `  ${idx + 1}. ${opt}\n`;
        });
        sec += `\n`;
      }
      if (data.title_options && data.title_options.length > 0) {
        sec += `Title Options:\n`;
        data.title_options.forEach((opt: string, idx: number) => {
          sec += `  ${idx + 1}. ${opt}\n`;
        });
        sec += `\n`;
      }
      if (data.best_title) {
        sec += `Best Title:\n  ${data.best_title}\n\n`;
      }
      if (data.title && !data.hook_options && !data.title_options && !data.best_title) {
        sec += `Title/Hook:\n  ${data.title}\n\n`;
      }
      if (data.best_cover_text) {
        sec += `Best Cover Text:\n  ${data.best_cover_text}\n\n`;
      }
      if (data.hook && !data.hook_options) {
        sec += `Hook:\n  ${data.hook}\n\n`;
      }
      if (data.caption) {
        sec += `Caption:\n  ${data.caption}\n\n`;
      }
      if (data.description) {
        sec += `Description:\n  ${data.description}\n\n`;
      }
      if (data.post) {
        sec += `Post Content:\n  ${data.post}\n\n`;
      }
      if (data.hashtags && data.hashtags.length > 0) {
        sec += `Recommended Hashtags:\n  ${data.hashtags.map((h: string) => `#${h}`).join(" ")}\n\n`;
      }
      if (data.keywords && data.keywords.length > 0) {
        sec += `Search Keywords / Tags:\n  ${data.keywords.join(", ")}\n\n`;
      }
      if (data.cta) {
        sec += `Call to Action (CTA):\n  ${data.cta}\n\n`;
      }
      return sec + `\n`;
    };

    output += formatSection("Instagram Reels", socialMetadata.instagram);
    output += formatSection("TikTok", socialMetadata.tiktok);
    output += formatSection("YouTube Shorts", socialMetadata.youtube);
    output += formatSection("Facebook Reels", socialMetadata.facebook);
    output += formatSection("Snapchat", socialMetadata.snapchat);
    output += formatSection("Pinterest", socialMetadata.pinterest);
    output += formatSection("X / Threads", socialMetadata.x_threads);

    const blob = new Blob([output], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `clip_social_metadata_pack.txt`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const renderField = (label: string, value: string | string[] | undefined, key: string, isList = false, isTags = false) => {
    if (!value || (Array.isArray(value) && value.length === 0)) return null;

    const copyText = Array.isArray(value)
      ? (isTags ? value.map(v => `#${v}`).join(" ") : value.join("\n"))
      : value;

    return (
      <div className="space-y-1 border-t border-neutral-100 pt-2.5 first:border-0 first:pt-0">
        <div className="flex justify-between items-center">
          <span className="text-[11px] font-bold text-neutral-400 uppercase tracking-wider">{label}</span>
          <button
            onClick={() => handleCopy(copyText, key)}
            className="text-xs text-neutral-500 hover:text-black flex items-center gap-1 transition-colors animate-fade-in"
          >
            {copiedField === `${activeTab}-${key}` ? (
              <>
                <Check className="w-3.5 h-3.5 text-green-600 animate-scale-in" />
                <span className="text-green-600 font-medium">Copied!</span>
              </>
            ) : (
              <>
                <Share2 className="w-3.5 h-3.5 text-neutral-400 group-hover:text-neutral-600" />
                <span>{isTags ? "Copy All" : "Copy"}</span>
              </>
            )}
          </button>
        </div>
        {isTags && Array.isArray(value) ? (
          <div className="flex flex-wrap gap-1 mt-1">
            {value.map((h, i) => (
              <Badge key={i} variant="outline" className="text-[10px] bg-neutral-50 text-neutral-600 font-medium px-2 py-0.5">
                {key === "hashtags" ? `#${h}` : h}
              </Badge>
            ))}
          </div>
        ) : isList && Array.isArray(value) ? (
          <ul className="list-decimal pl-4 text-xs text-neutral-700 space-y-1 mt-1 pr-8">
            {value.map((item, idx) => (
              <li key={idx} className="leading-relaxed">{item}</li>
            ))}
          </ul>
        ) : (
          <p className={`text-neutral-700 whitespace-pre-wrap leading-relaxed pr-8 ${key === "title" || key === "best_title" || key === "hook" ? "text-sm font-semibold text-neutral-900" : "text-xs"}`}>
            {value}
          </p>
        )}
      </div>
    );
  };

  return (
    <div className="mt-4 p-4 border border-neutral-100 rounded-xl bg-neutral-50/50 space-y-4 shadow-sm">
      <div className="flex items-center justify-between border-b border-neutral-100 pb-2">
        <h4 className="font-semibold text-sm text-neutral-800 flex items-center gap-1.5">
          <span>🚀</span> Social Upload Pack
        </h4>
        <div className="flex items-center gap-2">
          <button
            onClick={handleDownload}
            className="text-xs text-neutral-500 hover:text-black flex items-center gap-1 transition-colors border border-neutral-200 rounded px-2 py-1 bg-white hover:bg-neutral-50 shadow-sm"
            title="Download full metadata package as .txt file"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download Doc</span>
          </button>
          <span className="text-[10px] bg-neutral-200 text-neutral-600 px-2 py-0.5 rounded-full font-medium">AI-Generated</span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-1.5">
        {platforms.map((p) => {
          const hasPlatformData = !!socialMetadata[p.id];
          return (
            <button
              key={p.id}
              onClick={() => setActiveTab(p.id)}
              className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-all flex items-center gap-1.5 ${
                activeTab === p.id
                  ? "bg-black text-white shadow-sm"
                  : "bg-white text-neutral-600 hover:bg-neutral-100 border border-neutral-200/60"
              } ${!hasPlatformData ? "opacity-50 hover:opacity-100" : ""}`}
            >
              <span>{p.icon}</span>
              {p.label}
            </button>
          );
        })}
      </div>

      {/* Content Pack */}
      {currentPack ? (
        <div className="space-y-3 bg-white p-3 rounded-lg border border-neutral-100/80 shadow-inner">
          {/* Render hooks/titles if they exist */}
          {renderField("Hook Options", currentPack.hook_options, "hook_options", true)}
          {renderField("Title Options", currentPack.title_options, "title_options", true)}
          
          {/* Render Best Title / Title / Hook */}
          {renderField("Best Title", currentPack.best_title, "best_title")}
          {renderField("Title", currentPack.title, "title")}
          {renderField("Hook", currentPack.hook, "hook")}
          
          {/* Cover text */}
          {renderField("Best Cover Text", currentPack.best_cover_text, "best_cover_text")}
          
          {/* Captions / Descriptions / Post */}
          {renderField("Caption", currentPack.caption, "caption")}
          {renderField("Description", currentPack.description, "description")}
          {renderField("Post Content", currentPack.post, "post")}

          {/* CTAs */}
          {renderField("Call to Action (CTA)", currentPack.cta, "cta")}
          
          {/* Hashtags */}
          {renderField("Recommended Hashtags", currentPack.hashtags, "hashtags", false, true)}
          
          {/* Keywords */}
          {renderField("Search Keywords", currentPack.keywords, "keywords", false, true)}
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
