import { useState, useRef } from "react";
import { generateImage, pollJobStatus } from "../services/api";

const STYLES = [
  { id: "realistic",   label: "Realismo",       emoji: "📷" },
  { id: "anime",       label: "Anime",           emoji: "🌸" },
  { id: "oil_painting",label: "Pintura al óleo", emoji: "🖼️" },
  { id: "sketch",      label: "Boceto",          emoji: "✏️" },
  { id: "minimalist",  label: "Minimalista",     emoji: "⬜" },
];

export default function ImageGenerator({ userId }) {
  const [prompt, setPrompt]     = useState("");
  const [style, setStyle]       = useState("realistic");
  const [status, setStatus]     = useState("idle"); // idle | loading | polling | done | error
  const [jobStatus, setJobStatus] = useState(null);
  const [result, setResult]     = useState(null);
  const [error, setError]       = useState("");
  const [gallery, setGallery]   = useState([]);
  const pollTimeout             = useRef(null);

  const handleGenerate = async () => {
    if (!prompt.trim()) return;
    setStatus("loading");
    setError("");
    setResult(null);

    try {
      // 1. Iniciar job asíncrono
      const data = await generateImage(prompt, style, userId);

      if (data.error) {
        setError(data.error);
        setStatus("error");
        return;
      }

      // 2. Polling cada 3 segundos
      setStatus("polling");
      const final = await pollJobStatus(data.job_id, (update) => {
        setJobStatus(update);
      });

      if (final.status === "completed") {
        setResult(final);
        setGallery((prev) => [{ ...final, prompt, style }, ...prev.slice(0, 11)]);
        setStatus("done");
      } else {
        setError(final.error || "La imagen fue rechazada por el sistema de moderación.");
        setStatus("error");
      }
    } catch (err) {
      setError(err.message);
      setStatus("error");
    }
  };

  const isLoading = status === "loading" || status === "polling";

  return (
    <div className="page">
      <div className="page-header">
        <h1>Generación de Imágenes</h1>
        <p>Describe tu idea y elige un estilo. Stable Diffusion XL creará la imagen en ~20 segundos.</p>
      </div>

      <div className="generator-layout">
        {/* Panel de control */}
        <div className="control-panel">
          <div className="field">
            <label>Descripción de la imagen</label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Ej: oficina moderna con luz natural, estilo minimalista, plantas decorativas, escritorios de madera clara"
              rows={4}
              disabled={isLoading}
            />
            <span className="field-hint">
              Sé específico con colores, iluminación, composición y ambiente.
            </span>
          </div>

          <div className="field">
            <label>Estilo visual</label>
            <div className="style-grid">
              {STYLES.map((s) => (
                <button
                  key={s.id}
                  className={`style-btn ${style === s.id ? "selected" : ""}`}
                  onClick={() => setStyle(s.id)}
                  disabled={isLoading}
                >
                  <span>{s.emoji}</span>
                  <span>{s.label}</span>
                </button>
              ))}
            </div>
          </div>

          <button
            className="btn-primary"
            onClick={handleGenerate}
            disabled={isLoading || !prompt.trim()}
          >
            {isLoading ? "Generando..." : "✦ Generar imagen"}
          </button>

          {/* Estado del job */}
          {status === "polling" && jobStatus && (
            <div className="job-status">
              <div className="spinner" />
              <span>Estado: {jobStatus.status}...</span>
            </div>
          )}

          {error && <div className="error-box">{error}</div>}
        </div>

        {/* Resultado */}
        <div className="result-panel">
          {status === "done" && result?.image_url ? (
            <div className="image-result">
              <img src={result.image_url} alt={prompt} />
              <div className="image-meta">
                <span className="ai-badge">◈ Generado con IA</span>
                <span className="image-style">{STYLES.find((s) => s.id === style)?.label}</span>
              </div>
              <a
                href={result.image_url}
                download="imagen-generada.png"
                className="btn-secondary"
                target="_blank"
                rel="noreferrer"
              >
                ↓ Descargar imagen
              </a>
            </div>
          ) : (
            <div className="empty-result">
              {isLoading ? (
                <>
                  <div className="loading-animation">
                    <div className="loading-bar" />
                  </div>
                  <p>Generando tu imagen con Stable Diffusion XL...</p>
                  <small>Esto puede tomar entre 15 y 30 segundos</small>
                </>
              ) : (
                <>
                  <span className="empty-icon">🖼️</span>
                  <p>Tu imagen aparecerá aquí</p>
                </>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Galería de sesión */}
      {gallery.length > 0 && (
        <div className="gallery-section">
          <h2>Galería de sesión ({gallery.length})</h2>
          <div className="gallery-grid">
            {gallery.map((item, i) => (
              <div key={i} className="gallery-item">
                <img src={item.image_url} alt={item.prompt} />
                <div className="gallery-overlay">
                  <span>{item.prompt.slice(0, 60)}...</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
