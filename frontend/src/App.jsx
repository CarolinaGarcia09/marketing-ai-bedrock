import { useState } from "react";
import ImageGenerator from "./pages/ImageGenerator";
import TextEditor from "./pages/TextEditor";
import "./App.css";

const TABS = [
  { id: "images", label: "🎨 Generar Imágenes", roles: ["Designers", "Approvers"] },
  { id: "text",   label: "✍️ Editar Texto",      roles: ["Writers",   "Approvers"] },
];

// Demo: usuario simulado para desarrollo local sin Cognito real
const DEMO_USER = {
  id: "demo-user-001",
  name: "Leidy Carolina",
  role: "Approvers",
  email: "leidy@marketing-ai.demo",
};

export default function App() {
  const [activeTab, setActiveTab] = useState("images");
  const user = DEMO_USER; // En producción: viene de Cognito JWT

  const availableTabs = TABS.filter((t) => t.roles.includes(user.role));

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-brand">
          <span className="brand-icon">◈</span>
          <span className="brand-name">Marketing AI</span>
          <span className="brand-tag">powered by Amazon Bedrock</span>
        </div>
        <nav className="header-nav">
          {availableTabs.map((tab) => (
            <button
              key={tab.id}
              className={`nav-btn ${activeTab === tab.id ? "active" : ""}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </nav>
        <div className="header-user">
          <span className="user-role">{user.role}</span>
          <span className="user-name">{user.name}</span>
        </div>
      </header>

      <main className="app-main">
        {activeTab === "images" && <ImageGenerator userId={user.id} />}
        {activeTab === "text"   && <TextEditor userId={user.id} />}
      </main>
    </div>
  );
}
