import { useState, useRef } from "react";
import { editText } from "../services/api";

const OPERATIONS = [
  { id: "summarize",  label: "Resumir",             emoji: "📋", desc: "Extrae las ideas principales" },
  { id: "expand",     label: "Expandir",             emoji: "📖", desc: "Agrega contexto y ejemplos" },
  { id: "grammar",    label: "Corregir gramática",   emoji: "✅", desc: "Corrige sin cambiar el tono" },
  { id: "variations", label: "Generar variaciones",  emoji: "🔀", desc: "3 versiones con diferente enfoque" },
];

const MAX_TOKENS_ESTIMATE = 3000;

function estimateTokens(text) {
  return Math.floor(text.length / 4);
}

export default function TextEditor({ userId }) {
  const [inputText, setInputText]   = useState("");
  const [operation, setOperation]   = useState("grammar");
  const [result, setResult]         = useState(null);
  const [history, setHistory]       = useState([]);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState("");
  const docId                       = useRef(`doc-${Date.now()}`);
  const versionRef                  = useRef(0);

  const tokens = estimateTokens(inputText);
  const overLimit = tokens > MAX_TOKENS_ESTIMATE;

  const handleEdit = async () => {
    if (!inputText.trim() || overLimit) return;
    setLoading(true);
    setError("");

    try {
      const data = await editText(inputText, operation, docId.current, versionRef.current);

      if (data.error) {
        setError(data.error);
        return;
      }

      versionRef.current = data.version_number;
      setResult(data);
      setHistory((prev) => [
        {
          version: data.version_number,
          operation,
          original: inputText.slice(0, 100) + "...",
          edited: data.edited_text.slice(0, 100) + "...",
          ts: new Date().toLocaleTimeString("es-CO"),
        },
        ...prev.slice(0, 9),
      ]);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const applyResult = () => {
    if (result) {
      setInputText(result.edited_text);
      setResult(null);
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <h1>Edición de Contenido</h1>
        <p>Claude 3 Sonnet analiza y transforma tu texto según la operación seleccionada.</p>
      </div>

      <div className="editor-layout">
        {/* Operaciones */}
        <div className="operations-bar">
          {OPERATIONS.map((op) => (
            <button
              key={op.id}
              className={`op-btn ${operation === op.id ? "selected" : ""}`}
              onClick={() => setOperation(op.id)}
              disabled={loading}
              title={op.desc}
            >
              <span>{op.emoji}</span>
              <span>{op.label}</span>
            </button>
          ))}
        </div>

        <div className="editor-panels">
          {/* Panel de entrada */}
          <div className="editor-panel">
            <div className="panel-header">
              <span>Texto original</span>
              <span className={`token-counter ${overLimit ? "over-limit" : ""}`}>
                ~{tokens} / {MAX_TOKENS_ESTIMATE} tokens
              </span>
            </div>
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Pega o escribe aquí el texto que deseas editar..."
              disabled={loading}
            />
            {overLimit && (
              <div className="warning-box">
                ⚠️ El texto supera el límite de {MAX_TOKENS_ESTIMATE} tokens. Divide el contenido en secciones más pequeñas.
              </div>
            )}
            <button
              className="btn-primary"
              onClick={handleEdit}
              disabled={loading || !inputText.trim() || overLimit}
            >
              {loading ? "Procesando con Claude..." : `✦ ${OPERATIONS.find((o) => o.id === operation)?.label}`}
            </button>
            {error && <div className="error-box">{error}</div>}
          </div>

          {/* Panel de resultado */}
          <div className="editor-panel">
            <div className="panel-header">
              <span>Resultado — Claude 3 Sonnet</span>
              {result && <span className="version-badge">v{result.version_number}</span>}
            </div>
            {result ? (
              <>
                <div className="result-text">{result.edited_text}</div>
                <div className="result-actions">
                  <button className="btn-primary" onClick={applyResult}>
                    ↩ Usar como nuevo texto base
                  </button>
                  <button
                    className="btn-secondary"
                    onClick={() => navigator.clipboard.writeText(result.edited_text)}
                  >
                    📋 Copiar
                  </button>
                </div>
              </>
            ) : (
              <div className="empty-result">
                {loading ? (
                  <>
                    <div className="spinner large" />
                    <p>Claude está procesando tu texto...</p>
                  </>
                ) : (
                  <>
                    <span className="empty-icon">✍️</span>
                    <p>El texto editado aparecerá aquí</p>
                  </>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Historial de versiones */}
        {history.length > 0 && (
          <div className="history-section">
            <h2>Historial de versiones (DynamoDB)</h2>
            <table className="history-table">
              <thead>
                <tr>
                  <th>Versión</th>
                  <th>Operación</th>
                  <th>Texto original</th>
                  <th>Resultado</th>
                  <th>Hora</th>
                </tr>
              </thead>
              <tbody>
                {history.map((h, i) => (
                  <tr key={i}>
                    <td><span className="version-badge">v{h.version}</span></td>
                    <td>{OPERATIONS.find((o) => o.id === h.operation)?.label}</td>
                    <td className="text-truncate">{h.original}</td>
                    <td className="text-truncate">{h.edited}</td>
                    <td>{h.ts}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
