# SupoClip - KK Edition

Welcome to the **KK Edition** of SupoClip—a customized, production-ready fork optimized for high-volume video editors, professional content creators, and resilient API usage.

This edition builds on top of the robust open-source foundations of SupoClip and introduces key features addressing storage organization, source quality, model redundancy, and metadata generation safety.

---

## 🚀 Key Enhancements in KK Edition

### 1. Editable Generation Names & Preservation of Source Titles
- Rename video generation tasks dynamically within the UI.
- The Generation Name acts as the primary project title.
- The original video title is neatly preserved and displayed as a subtitle below the generation name (e.g. `Original video: {source_title}`).
- Persisted in Neon PostgreSQL database with built-in schema fallback compatibility.

### 2. Custom Structured High-Quality Directories
Outputs are organized into clean, permanent, structured directories:
- **Source Downloads & Uploads**: Saved to `outputs/{generation_name}/{generation_name}.mp4` (or matching container extension).
- **Output Clip Folders**: Clipped highlights are rendered directly to `outputs/{generation_name}/clips/Clip_{index}_{sanitized_hook_title}.mp4`.
- **Local Video Copying**: Uploaded local videos are automatically copied to the generation folder to keep all media files grouped.
- **File Sanitization**: Invalid characters (`\/*?:"<>|`) are automatically stripped using the custom filename sanitization engine.

### 3. Maximum Video Quality Downloads
- YouTube downloading format has been upgraded to:
  ```python
  "format": "bestvideo+bestaudio/best"
  ```
- Automatically pulls the highest quality stream available (supporting 4K/2K/1080p source downloads) without downscaling or capping.

### 4. Automatic Google Gemini Model Fallbacks
To resolve API rate limits and daily quota limits (HTTP `429` / Resource Exhausted errors), the system automatically rotates through fallback candidates in sequence:
1. `gemini-3-flash` / `gemini-3-flash-preview` (default configured model)
2. `gemini-3.5-flash`
3. `gemini-3.1-flash-lite` (providing a large **500 Requests Per Day** quota!)
4. `gemini-2.5-flash`
5. `gemini-3.6-flash`
6. `gemini-2.5-flash-lite`

This fallback cycling is applied seamlessly to both **Transcript Analysis** (Phase 1) and **Social Media Upload Pack** generation (Phase 2).

### 5. Resilient Social Media Upload Pack
- **Transient Retry Engine**: Failed API requests automatically retry up to 2 times per candidate model using an exponential backoff retry loop (handles transient rate limits and server overloads).
- **Dynamic NLP Fallback Generator**: If all LLM APIs or quotas are completely exhausted, the system falls back to an offline rule-based processor (`build_dynamic_social_fallback`) that parses the clip transcript and hook to construct:
  - 3 platform-tailored title/hook variations.
  - Platform-native descriptions/captions.
  - Capitalized noun-extracted hashtags.
  - Platforms-specific custom CTAs for all 7 supported networks: Instagram Reels, TikTok, YouTube Shorts, Facebook Reels, Snapchat, Pinterest, and X/Threads.

---

## 🛠️ Verification & Test Suite
The KK Edition has been validated against all existing tests:
- **Backend Tests**: 128 tests passed successfully (`uv run pytest`) with 83.85% coverage.
- **Frontend Typechecks & Unit Tests**: 55 tests passed successfully (`pnpm test` and `npx tsc --noEmit`).

---

## 📄 License
This edition is licensed under the same AGPL-3.0 License as the upstream repository.
