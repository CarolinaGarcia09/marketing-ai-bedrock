# Guía de Despliegue — Marketing AI con Amazon Bedrock

## Paso 1 — Crear repositorio en GitHub

```bash
# En tu máquina local, dentro de la carpeta del proyecto:
git init
git add .
git commit -m "feat: implementación inicial Marketing AI con Amazon Bedrock"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/marketing-ai-bedrock.git
git push -u origin main
```

---

## Paso 2 — Habilitar modelos en Amazon Bedrock

1. Ir a la consola de AWS → **Amazon Bedrock**
2. En el menú lateral: **Model access**
3. Solicitar acceso a:
   - ✅ `Stability AI — Stable Diffusion XL 1.0`
   - ✅ `Anthropic — Claude 3 Sonnet`
4. Esperar aprobación (puede tomar de minutos a 48h según el modelo)

---

## Paso 3 — Configurar credenciales AWS

```bash
# Nunca usar credenciales root
aws configure
# AWS Access Key ID: [de un usuario IAM de desarrollo]
# AWS Secret Access Key: [clave secreta]
# Default region: us-east-1
# Default output format: json
```

---

## Paso 4 — Desplegar infraestructura con CDK

```bash
cd backend/infrastructure

# Crear entorno virtual Python
python -m venv .venv
source .venv/bin/activate          # Linux/Mac
# .venv\Scripts\activate           # Windows

pip install -r requirements.txt

# Bootstrap CDK (solo la primera vez por cuenta/región)
cdk bootstrap aws://TU_ACCOUNT_ID/us-east-1

# Revisar qué se va a crear
cdk diff

# Desplegar
cdk deploy

# Al finalizar, anota los Outputs:
# ✅ ApiUrl      → URL de la API REST
# ✅ UserPoolId  → Para Cognito
# ✅ UserPoolClientId
# ✅ FrontendUrl → URL de CloudFront
```

---

## Paso 5 — Crear usuarios en Cognito

```bash
# Crear usuario diseñador
aws cognito-idp admin-create-user \
  --user-pool-id TU_USER_POOL_ID \
  --username diseñador@empresa.com \
  --temporary-password Temp1234! \
  --user-attributes Name=email,Value=diseñador@empresa.com

# Agregar al grupo Designers
aws cognito-idp admin-add-user-to-group \
  --user-pool-id TU_USER_POOL_ID \
  --username diseñador@empresa.com \
  --group-name Designers

# Repetir para Writers y Approvers según necesidad
```

---

## Paso 6 — Configurar y desplegar el Frontend

```bash
cd frontend

# Instalar dependencias
npm install

# Configurar variables de entorno con los Outputs del CDK
cp .env.example .env
# Editar .env con los valores reales

# Desarrollo local
npm run dev
# → http://localhost:5173

# Build para producción
npm run build

# Subir a S3 (reemplaza con tu bucket de frontend)
aws s3 sync dist/ s3://marketing-ai-frontend-TU_ACCOUNT_ID --delete

# Invalidar caché de CloudFront
aws cloudfront create-invalidation \
  --distribution-id TU_DISTRIBUTION_ID \
  --paths "/*"
```

---

## Verificación del despliegue

```bash
# Probar endpoint de generación de imágenes
curl -X POST https://TU_API_URL/generate-image \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TU_JWT_TOKEN" \
  -d '{"prompt": "oficina moderna", "style": "realistic", "user_id": "test"}'

# Respuesta esperada:
# {"job_id": "uuid", "status": "pending"}

# Consultar estado del job
curl https://TU_API_URL/job-status/TU_JOB_ID \
  -H "Authorization: Bearer TU_JWT_TOKEN"
```

---

## Costos esperados (primera semana de pruebas)

Con uso moderado de pruebas (~50 imágenes, ~10,000 tokens):
- **Bedrock**: ~$0.80 USD
- **Lambda + API Gateway**: < $0.10 USD
- **S3 + DynamoDB**: < $0.05 USD
- **Total aproximado**: < $1 USD

Para destruir toda la infraestructura después de las pruebas:
```bash
cdk destroy
```
