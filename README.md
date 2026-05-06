# Marketing AI — Generación de Imágenes y Edición de Contenido con Amazon Bedrock

Aplicación web de IA generativa para equipos creativos de marketing, desarrollada sobre AWS con Amazon Bedrock como capa de acceso unificada a modelos fundacionales.

> **Caso Práctico — Unidad 3 | Leidy Carolina Ricaurte Garcia | Mayo 2026**

---

## 📐 Arquitectura

```
Usuario → React SPA (S3 + CloudFront)
             ↓ HTTPS
        API Gateway (REST)
          ↙           ↘
   Lambda              Lambda
  (Imágenes)          (Texto/Claude)
       ↓                   ↓
  Amazon Bedrock      Amazon Bedrock
  Stable Diffusion XL  Claude 3 Sonnet
       ↓                   ↓
   Amazon S3          DynamoDB
  (imágenes)         (historial)
```

##  Stack Tecnológico

| Capa | Servicio |
|------|----------|
| IA — Imágenes | Amazon Bedrock / Stable Diffusion XL |
| IA — Texto | Amazon Bedrock / Claude 3 Sonnet |
| Backend | AWS Lambda (Python 3.12) |
| API | Amazon API Gateway |
| Almacenamiento | Amazon S3 (AES-256) |
| Base de datos | Amazon DynamoDB |
| Autenticación | Amazon Cognito |
| Moderación | Amazon Rekognition |
| Frontend | React.js + Vite |
| IaC | AWS CDK (Python) |

---

##  Estructura del Repositorio

```
marketing-ai-bedrock/
├── backend/
│   ├── lambdas/
│   │   ├── generate_image/     # Generación con Stable Diffusion XL
│   │   ├── edit_text/          # Edición de texto con Claude 3 Sonnet
│   │   ├── job_status/         # Polling de estado de jobs asincrónicos
│   │   └── moderate/           # Moderación con Rekognition
│   └── infrastructure/
│       ├── app.py              # Entry point CDK
│       └── stacks/
│           └── marketing_ai_stack.py
├── frontend/
│   ├── src/
│   │   ├── components/         # Componentes reutilizables
│   │   ├── pages/              # Vistas principales
│   │   ├── hooks/              # Custom hooks
│   │   └── services/           # Llamadas a la API
│   └── package.json
└── docs/
    └── architecture.md
```

---

##  Despliegue

### Pre-requisitos

- AWS CLI configurado con credenciales válidas
- Python 3.12+
- Node.js 18+
- AWS CDK instalado: `npm install -g aws-cdk`
- Acceso habilitado en Amazon Bedrock para:
  - `stability.stable-diffusion-xl-v1`
  - `anthropic.claude-3-sonnet-20240229-v1:0`

### 1. Infraestructura (CDK)

```bash
cd backend/infrastructure
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cdk bootstrap
cdk deploy
```

### 2. Frontend

```bash
cd frontend
npm install
# Copiar las URLs de salida del CDK al .env
cp .env.example .env
npm run dev       # Desarrollo local
npm run build     # Build para producción
```

---

##  Roles de Usuario

| Rol | Permisos |
|-----|----------|
| `Designers` | Generación de imágenes, galería, comentarios |
| `Writers` | Edición de texto, historial de versiones, comentarios |
| `Approvers` | Acceso completo + aprobación/rechazo de contenido |

---

##  Costo Estimado Mensual

Basado en 1,000 imágenes/mes y 500,000 tokens de texto/mes:

| Servicio | Costo |
|----------|-------|
| Bedrock — Stable Diffusion XL | $8.00 |
| Bedrock — Claude 3 Sonnet | $9.00 |
| Lambda | $1.20 |
| S3 | $0.50 |
| DynamoDB | $2.00 |
| API Gateway | $0.18 |
| Rekognition | $1.00 |
| CloudFront | $0.50 |
| **Total estimado** | **$22.38 USD/mes** |

---

##  Seguridad (Defensa en Profundidad)

1. **Red**: Todo el tráfico por HTTPS, HTTP rechazado en API Gateway
2. **Autenticación**: JWT validado por Cognito antes de llegar a Lambda
3. **Autorización**: Verificación de `cognito:groups` en cada Lambda
4. **Validación de entrada**: Filtro de términos prohibidos en prompts
5. **Moderación de salida**: Rekognition analiza cada imagen generada
6. **Cifrado**: S3 AES-256 en reposo, DynamoDB cifrado por defecto
7. **Auditoría**: CloudTrail + CloudWatch con retención de 90 días

---

##  Consideraciones Éticas

- Todas las imágenes generadas llevan metadato `ai_generated: true` y marca de agua
- Los prompts y resultados no se usan para reentrenar modelos (acuerdo contractual con AWS)
- Revisión mensual de prompts para detectar sesgos de género, etnia o edad
- Logs de usuarios internos cifrados con política de retención de 90 días
