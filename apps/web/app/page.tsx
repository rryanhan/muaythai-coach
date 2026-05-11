"use client";

import type { CSSProperties, FormEvent } from "react";
import { useEffect, useMemo, useRef, useState } from "react";

type Stance = "orthodox" | "southpaw";
type CaptureMode = "camera" | "upload";
type ClipSource = "recorded" | "uploaded";
type CalibrationStepId = "front" | "lead" | "rear" | "reach";

type JabRep = {
  rep_number: number;
  extension_time_ms: number;
  extension_speed_normalized: number;
  peak_extension_velocity_normalized: number;
  return_time_ms: number;
  rear_hand_dropped: boolean;
  hand_dip_telegraph: boolean;
  pre_jab_dip_normalized: number;
  timing_confidence: string;
};

type AnalysisResponse = {
  status: "complete";
  filename: string;
  stance: Stance;
  metrics: {
    detected_reps: number;
    rear_hand_drops: number;
    hand_dip_telegraphs: number;
    average_extension_time_ms: number | null;
    average_extension_speed_normalized: number | null;
    average_peak_extension_velocity_normalized: number | null;
    average_return_time_ms: number | null;
    confidence: string;
    reps: JabRep[];
  };
  diagnostics: {
    pose_visibility_ratio: number;
    total_frames: number;
    landmarks: Record<
      string,
      {
        visibility_ratio: number;
        average_confidence_when_visible: number | null;
      }
    >;
  };
  overlay_url: string | null;
  result_url: string;
};

type CoachingCard = {
  label: string;
  value: string;
  detail: string;
  tone: "good" | "warning" | "neutral";
};

const API_BASE_URL = process.env.NEXT_PUBLIC_ANALYSIS_API_URL ?? "http://localhost:8000";
const ROUND_SECONDS = 60;

const calibrationSteps: Array<{ id: CalibrationStepId; label: string; angle: string }> = [
  { id: "front", label: "Guard", angle: "Front" },
  { id: "lead", label: "Guard", angle: "Lead side" },
  { id: "rear", label: "Guard", angle: "Rear side" },
  { id: "reach", label: "Reach", angle: "Hands out" }
];

export default function Home() {
  const cameraPreviewRef = useRef<HTMLVideoElement | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const recordedChunksRef = useRef<Blob[]>([]);
  const previewUrlRef = useRef<string | null>(null);

  const [captureMode, setCaptureMode] = useState<CaptureMode>("camera");
  const [clipSource, setClipSource] = useState<ClipSource | null>(null);
  const [video, setVideo] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [completedCalibrationSteps, setCompletedCalibrationSteps] = useState<CalibrationStepId[]>(
    []
  );
  const [stance, setStance] = useState<Stance>("orthodox");
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const currentCalibrationStep = calibrationSteps.find(
    (step) => !completedCalibrationSteps.includes(step.id)
  );
  const calibrationComplete = completedCalibrationSteps.length === calibrationSteps.length;
  const roundProgress = Math.min(recordingSeconds / ROUND_SECONDS, 1);

  const overlayUrl = useMemo(() => {
    if (!result?.overlay_url) {
      return null;
    }
    return new URL(result.overlay_url, API_BASE_URL).toString();
  }, [result]);

  const coachingCards = useMemo(() => {
    if (!result) {
      return [];
    }
    return buildCoachingCards(result);
  }, [result]);

  useEffect(() => {
    if (cameraPreviewRef.current && cameraStream) {
      cameraPreviewRef.current.srcObject = cameraStream;
    }
  }, [cameraStream]);

  useEffect(() => {
    if (!isRecording) {
      return undefined;
    }

    const intervalId = window.setInterval(() => {
      setRecordingSeconds((seconds) => {
        const nextSeconds = seconds + 1;
        if (nextSeconds >= ROUND_SECONDS && recorderRef.current?.state === "recording") {
          recorderRef.current.stop();
        }
        return Math.min(nextSeconds, ROUND_SECONDS);
      });
    }, 1000);

    return () => window.clearInterval(intervalId);
  }, [isRecording]);

  useEffect(() => {
    return () => {
      stopCameraTracks(cameraStream);
      if (previewUrlRef.current) {
        URL.revokeObjectURL(previewUrlRef.current);
      }
    };
  }, [cameraStream]);

  async function startCamera() {
    setError(null);
    setCaptureMode("camera");

    if (!navigator.mediaDevices?.getUserMedia) {
      setError(
        "This browser does not expose camera recording here. Open localhost in Chrome or Safari, or upload a saved clip."
      );
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: {
          facingMode: "user",
          width: { ideal: 720 },
          height: { ideal: 1280 }
        }
      });
      setCameraStream(stream);
    } catch (caught) {
      setError(cameraErrorMessage(caught));
    }
  }

  function markCalibrationStep() {
    if (!currentCalibrationStep) {
      return;
    }
    setCompletedCalibrationSteps((steps) => [...steps, currentCalibrationStep.id]);
  }

  function resetCalibration() {
    setCompletedCalibrationSteps([]);
    setRecordingSeconds(0);
  }

  function startRecording() {
    if (!cameraStream) {
      setError("Start the camera first.");
      return;
    }
    if (!calibrationComplete) {
      setError("Complete calibration first.");
      return;
    }

    recordedChunksRef.current = [];
    setRecordingSeconds(0);
    setResult(null);
    setError(null);

    const mimeType = getSupportedRecordingMimeType();
    const recorder = new MediaRecorder(cameraStream, mimeType ? { mimeType } : undefined);
    recorderRef.current = recorder;

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        recordedChunksRef.current.push(event.data);
      }
    };

    recorder.onstop = () => {
      const blob = new Blob(recordedChunksRef.current, {
        type: recorder.mimeType || "video/webm"
      });
      const extension = blob.type.includes("mp4") ? "mp4" : "webm";
      const file = new File([blob], `shadowboxing-round.${extension}`, { type: blob.type });
      setSelectedClip(file, "recorded");
      setIsRecording(false);
    };

    recorder.start();
    setIsRecording(true);
  }

  function stopRecording() {
    if (recorderRef.current?.state === "recording") {
      recorderRef.current.stop();
    }
  }

  function handleUpload(file: File | null) {
    if (!file) {
      return;
    }
    setSelectedClip(file, "uploaded");
    setCaptureMode("upload");
    setResult(null);
    setError(null);
  }

  function setSelectedClip(file: File, source: ClipSource) {
    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current);
    }

    const nextPreviewUrl = URL.createObjectURL(file);
    previewUrlRef.current = nextPreviewUrl;
    setPreviewUrl(nextPreviewUrl);
    setVideo(file);
    setClipSource(source);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!video) {
      setError("Choose or record a round first.");
      return;
    }

    setIsAnalyzing(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    formData.append("video", video);
    formData.append("stance", stance);

    try {
      const response = await fetch(`${API_BASE_URL}/analyze/jab`, {
        method: "POST",
        body: formData
      });
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(payload?.detail ?? "Analysis failed.");
      }
      setResult((await response.json()) as AnalysisResponse);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Analysis failed.");
    } finally {
      setIsAnalyzing(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="round-stage" aria-labelledby="round-title">
        <div className="topbar">
          <div>
            <p className="kicker">Shadowboxing</p>
            <h1 id="round-title">Round Room</h1>
          </div>
          <div className="round-timer" style={{ "--progress": roundProgress } as CSSProperties}>
            <span>{formatTimer(recordingSeconds)}</span>
          </div>
        </div>

        <div className="mode-tabs" role="tablist" aria-label="Capture mode">
          <button
            aria-selected={captureMode === "camera"}
            className="mode-tab"
            type="button"
            onClick={() => setCaptureMode("camera")}
          >
            Camera
          </button>
          <button
            aria-selected={captureMode === "upload"}
            className="mode-tab"
            type="button"
            onClick={() => setCaptureMode("upload")}
          >
            Upload
          </button>
        </div>

        <div className="camera-surface">
          {captureMode === "camera" ? (
            <>
              <video
                ref={cameraPreviewRef}
                autoPlay
                className="camera-preview"
                muted
                playsInline
              />
              {!cameraStream ? <div className="empty-camera">Camera standby</div> : null}
              <div className="camera-hud">
                <span>{isRecording ? "Live" : "Boxing"}</span>
                <span>60s</span>
              </div>
              <div className="corner-markers" aria-hidden="true" />
            </>
          ) : (
            <label className="upload-dropzone">
              <input
                accept="video/mp4,video/quicktime,video/webm"
                type="file"
                onChange={(event) => handleUpload(event.target.files?.[0] ?? null)}
              />
              <span>{video && clipSource === "uploaded" ? video.name : "Select round video"}</span>
            </label>
          )}
        </div>

        <div className="calibration-panel" data-complete={calibrationComplete}>
          <div className="section-heading">
            <h2>Calibration</h2>
            <button className="text-action" type="button" onClick={resetCalibration}>
              Reset
            </button>
          </div>
          <div className="calibration-rail">
            {calibrationSteps.map((step) => (
              <div
                className="calibration-step"
                data-active={currentCalibrationStep?.id === step.id}
                data-done={completedCalibrationSteps.includes(step.id)}
                key={step.id}
              >
                <span>{step.angle}</span>
                <strong>{step.label}</strong>
              </div>
            ))}
          </div>
          <button
            className="calibration-action"
            disabled={!cameraStream || calibrationComplete}
            type="button"
            onClick={markCalibrationStep}
          >
            {calibrationComplete ? "Calibrated" : "Capture pose"}
          </button>
        </div>

        <form className="round-form" onSubmit={handleSubmit}>
          <fieldset className="stance-control">
            <legend>Stance</legend>
            <label>
              <input
                checked={stance === "orthodox"}
                name="stance"
                type="radio"
                onChange={() => setStance("orthodox")}
              />
              Orthodox
            </label>
            <label>
              <input
                checked={stance === "southpaw"}
                name="stance"
                type="radio"
                onChange={() => setStance("southpaw")}
              />
              Southpaw
            </label>
          </fieldset>

          {captureMode === "camera" ? (
            <div className="record-actions">
              <button
                className="secondary-action"
                disabled={isRecording || Boolean(cameraStream)}
                type="button"
                onClick={startCamera}
              >
                {cameraStream ? "Camera ready" : "Start camera"}
              </button>
              <button
                className="record-action"
                disabled={!cameraStream || !calibrationComplete}
                type="button"
                onClick={isRecording ? stopRecording : startRecording}
              >
                {isRecording ? "Stop round" : "Start round"}
              </button>
            </div>
          ) : null}

          {previewUrl ? (
            <div className="clip-preview">
              <video controls playsInline src={previewUrl}>
                <track kind="captions" />
              </video>
              <span>{clipSource === "recorded" ? "Recorded round" : "Uploaded round"}</span>
            </div>
          ) : null}

          <button className="primary-action" disabled={isAnalyzing || !video} type="submit">
            {isAnalyzing ? "Reading round..." : "Review round"}
          </button>
        </form>

        {error ? <p className="error-message">{error}</p> : null}
      </section>

      {result ? (
        <section className="review" aria-label="Round review">
          <div className="review-hero">
            <p className="kicker">Round review</p>
            <h2>{result.metrics.detected_reps} active strikes found</h2>
            <span>{result.metrics.confidence} confidence</span>
          </div>

          <div className="review-grid">
            <section className="review-panel" aria-labelledby="strike-title">
              <div className="section-heading">
                <h3 id="strike-title">Strike Mix</h3>
                <span>Boxing</span>
              </div>
              <StrikeBar label="Jab" value={result.metrics.detected_reps} max={12} />
              <StrikeBar label="Cross" value={0} max={12} pending />
              <StrikeBar label="Hook" value={0} max={12} pending />
              <StrikeBar label="Uppercut" value={0} max={12} pending />
            </section>

            <section className="review-panel movement-panel" aria-labelledby="movement-title">
              <div className="section-heading">
                <h3 id="movement-title">Movement</h3>
                <span>Direction</span>
              </div>
              <div className="movement-grid">
                {["Back", "Left", "Center", "Right", "Forward"].map((direction) => (
                  <div className="movement-cell" key={direction}>
                    <strong>--</strong>
                    <span>{direction}</span>
                  </div>
                ))}
              </div>
            </section>
          </div>

          <div className="coach-card-list">
            {coachingCards.map((card) => (
              <article className="coach-card" data-tone={card.tone} key={card.label}>
                <span>{card.label}</span>
                <strong>{card.value}</strong>
                <p>{card.detail}</p>
              </article>
            ))}
          </div>

          <section className="feedback-strip" aria-labelledby="feedback-title">
            <div className="section-heading">
              <h3 id="feedback-title">Feedback Clips</h3>
              <span>Next pass</span>
            </div>
            <div className="clip-slot-list">
              {["Feet crossing", "Short cross", "Jab repeat"].map((label) => (
                <article className="clip-slot" key={label}>
                  <div />
                  <strong>{label}</strong>
                  <span>Clip pending</span>
                </article>
              ))}
            </div>
          </section>

          <div className="metric-grid">
            <Metric label="Return avg" value={formatMs(result.metrics.average_return_time_ms)} />
            <Metric
              label="Extension avg"
              value={formatMs(result.metrics.average_extension_time_ms)}
            />
            <Metric label="Frames read" value={result.diagnostics.total_frames} />
          </div>

          {overlayUrl ? (
            <video className="overlay-player" controls playsInline src={overlayUrl}>
              <track kind="captions" />
            </video>
          ) : (
            <p className="fast-result-note">
              Fast preview mode skips overlay rendering and downsamples the clip for quicker feedback.
            </p>
          )}

          <div className="diagnostics">
            <h3>Tracking</h3>
            <div className="tracking-row">
              <span>Pose visibility</span>
              <strong>{formatPercent(result.diagnostics.pose_visibility_ratio)}</strong>
            </div>
            <div className="landmark-strip">
              {["left_wrist", "right_wrist", "left_elbow", "right_elbow"].map((name) => (
                <span key={name}>
                  {name.replace("_", " ")}{" "}
                  {formatPercent(result.diagnostics.landmarks[name]?.visibility_ratio ?? 0)}
                </span>
              ))}
            </div>
          </div>
        </section>
      ) : null}
    </main>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <article className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function StrikeBar({
  label,
  max,
  pending,
  value
}: {
  label: string;
  max: number;
  pending?: boolean;
  value: number;
}) {
  const width = pending ? 0 : Math.min(value / max, 1) * 100;
  return (
    <div className="strike-row" data-pending={pending}>
      <div>
        <span>{label}</span>
        <strong>{pending ? "--" : value}</strong>
      </div>
      <div className="strike-track">
        <span style={{ width: `${width}%` }} />
      </div>
    </div>
  );
}

function buildCoachingCards(result: AnalysisResponse): CoachingCard[] {
  const { metrics } = result;
  return [
    {
      label: "Lead hand dip",
      value: `${metrics.hand_dip_telegraphs}/${metrics.detected_reps}`,
      detail:
        metrics.hand_dip_telegraphs > 0
          ? "Lead hand dropped before the jab sequence."
          : "Lead hand stayed quiet before detected jabs.",
      tone: metrics.hand_dip_telegraphs > 0 ? "warning" : "good"
    },
    {
      label: "Rear guard",
      value: `${metrics.rear_hand_drops}/${metrics.detected_reps}`,
      detail:
        metrics.rear_hand_drops > 0
          ? "Rear hand opened during the jab sequence."
          : "Rear hand stayed near guard.",
      tone: metrics.rear_hand_drops > 0 ? "warning" : "good"
    },
    {
      label: "Tracking",
      value: formatPercent(result.diagnostics.pose_visibility_ratio),
      detail:
        result.diagnostics.pose_visibility_ratio >= 0.8
          ? "Pose signal was strong enough for review."
          : "Pose signal was limited; use more light and distance.",
      tone: result.diagnostics.pose_visibility_ratio >= 0.8 ? "good" : "warning"
    }
  ];
}

function getSupportedRecordingMimeType() {
  const types = ["video/mp4", "video/webm;codecs=vp9", "video/webm;codecs=vp8", "video/webm"];
  return types.find((type) => MediaRecorder.isTypeSupported(type));
}

function cameraErrorMessage(caught: unknown) {
  const errorName = caught instanceof DOMException ? caught.name : "";
  if (errorName === "NotAllowedError" || errorName === "SecurityError") {
    return "Camera permission was blocked. Allow camera access in the browser, or upload a saved clip.";
  }
  if (errorName === "NotFoundError" || errorName === "OverconstrainedError") {
    return "No usable camera was found. Try a normal browser window or upload a saved clip.";
  }
  return "Camera could not start in this browser. Try Chrome or Safari at localhost, or upload a saved clip.";
}

function stopCameraTracks(stream: MediaStream | null) {
  stream?.getTracks().forEach((track) => track.stop());
}

function formatTimer(seconds: number) {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`;
}

function formatMs(value: number | null) {
  return value === null ? "n/a" : `${value} ms`;
}

function formatPercent(value: number) {
  return `${Math.round(value * 100)}%`;
}
