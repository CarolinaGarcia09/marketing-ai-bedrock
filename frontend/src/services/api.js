const API_BASE = import.meta.env.VITE_API_URL;

function getToken() {
  return localStorage.getItem("id_token") || "";
}

function authHeaders() {
  return {
    "Content-Type": "application/json",
    Authorization: getToken(),
  };
}

// ── Generación de imágenes ─────────────────────────────────────────────────

export async function generateImage(prompt, style, userId) {
  const res = await fetch(`${API_BASE}/generate-image`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ prompt, style, user_id: userId }),
  });
  return res.json();
}

export async function pollJobStatus(jobId, onUpdate, intervalMs = 3000, maxAttempts = 30) {
  let attempts = 0;
  return new Promise((resolve, reject) => {
    const timer = setInterval(async () => {
      attempts++;
      try {
        const res = await fetch(`${API_BASE}/job-status/${jobId}`, {
          headers: authHeaders(),
        });
        const data = await res.json();
        onUpdate(data);

        if (data.status === "completed" || data.status === "failed" || data.status === "rejected") {
          clearInterval(timer);
          resolve(data);
        }

        if (attempts >= maxAttempts) {
          clearInterval(timer);
          reject(new Error("Tiempo de espera agotado"));
        }
      } catch (err) {
        clearInterval(timer);
        reject(err);
      }
    }, intervalMs);
  });
}

// ── Edición de texto ───────────────────────────────────────────────────────

export async function editText(text, operation, documentId, versionNumber = 0) {
  const res = await fetch(`${API_BASE}/edit-text`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ text, operation, document_id: documentId, version_number: versionNumber }),
  });
  return res.json();
}
